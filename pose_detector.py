from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from camera import Camera


LandmarkData = Dict[str, float]
PlayerLandmarks = Dict[int, LandmarkData]


@dataclass(frozen=True)
class PoseDetectorConfig:
    model_path: str = "pose_landmarker_heavy.task"
    max_players: int = 2
    smoothing_alpha: float = 0.35
    fps: int = 30


class LandmarkSmoother:
    def __init__(self, alpha: float = 0.35):
        self.alpha = alpha
        self.previous: Dict[Tuple[int, int], LandmarkData] = {}

    def smooth_landmark(
        self,
        player_id: int,
        landmark_id: int,
        landmark,
        mirror_x: bool = False,
    ) -> LandmarkData:
        key = (player_id, landmark_id)
        x = 1.0 - landmark.x if mirror_x else landmark.x
        current = {
            "x": x,
            "y": landmark.y,
            "z": landmark.z,
            "visibility": landmark.visibility,
            "presence": landmark.presence,
        }

        if key not in self.previous:
            self.previous[key] = current
            return current

        previous = self.previous[key]
        smoothed = {
            "x": previous["x"] * (1 - self.alpha) + current["x"] * self.alpha,
            "y": previous["y"] * (1 - self.alpha) + current["y"] * self.alpha,
            "z": previous["z"] * (1 - self.alpha) + current["z"] * self.alpha,
            "visibility": current["visibility"],
            "presence": current["presence"],
        }

        self.previous[key] = smoothed
        return smoothed

    def smooth_pose(
        self,
        player_id: int,
        pose_landmarks,
        tracked_ids: Iterable[int],
        mirror_x: bool = False,
    ) -> PlayerLandmarks:
        return {
            landmark_id: self.smooth_landmark(
                player_id,
                landmark_id,
                pose_landmarks[landmark_id],
                mirror_x=mirror_x,
            )
            for landmark_id in tracked_ids
        }


class PoseDetector:
    TRACKED_LANDMARKS = [
        0,
        7,
        8,
        11,
        12,
        13,
        14,
        15,
        16,
        23,
        24,
    ]
    
    CONNECTIONS = [
        (7, 0),
        (0, 8),
        (11, 12),
        (11, 13),
        (13, 15),
        (12, 14),
        (14, 16),
        (11, 23),
        (12, 24),
        (23, 24),
    ]

    def __init__(self, config: PoseDetectorConfig | None = None, camera: Camera | None = None):
        self.config = config or PoseDetectorConfig()
        self.camera = camera or Camera()
        self.smoother = LandmarkSmoother(alpha=self.config.smoothing_alpha)
        self.frame_index = 0

        base_options = python.BaseOptions(model_asset_path=self.config.model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=self.config.max_players,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarker = vision.PoseLandmarker.create_from_options(options)

    def process_frame(self, frame=None):
        if frame is None:
            if self.camera is None:
                raise RuntimeError("PoseDetector에 Camera가 연결되어 있지 않습니다.")

            frame = self.camera.get_frame()
            if frame is None:
                return None, {}

        drawn_frame = cv2.flip(frame, 1)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        timestamp_ms = int(self.frame_index * 1000 / self.config.fps)
        self.frame_index += 1

        result = self.landmarker.detect_for_video(mp_image, timestamp_ms)
        poses = result.pose_landmarks or []
        sorted_poses = sorted(poses, key=lambda pose: self._get_pose_center_x(pose, mirror_x=True))

        landmarks_by_player: Dict[int, PlayerLandmarks] = {}

        for player_id, pose_landmarks in enumerate(sorted_poses[: self.config.max_players]):
            smoothed_landmarks = self.smoother.smooth_pose(
                player_id=player_id,
                pose_landmarks=pose_landmarks,
                tracked_ids=self.TRACKED_LANDMARKS,
                mirror_x=True,
            )
            landmarks_by_player[player_id] = smoothed_landmarks
            self._draw_landmarks(drawn_frame, smoothed_landmarks)

        return drawn_frame, landmarks_by_player

    

    def close(self):
        self.landmarker.close()
        if self.camera is not None:
            self.camera.close()

    @staticmethod
    def _get_pose_center_x(pose_landmarks, mirror_x: bool = False) -> float:
        key_indices = [11, 12, 23, 24]
        xs = [
            1.0 - pose_landmarks[index].x if mirror_x else pose_landmarks[index].x
            for index in key_indices
        ]
        return sum(xs) / len(xs)

    @staticmethod
    def _to_pixel(landmark: LandmarkData, width: int, height: int) -> Tuple[int, int]:
        return int(landmark["x"] * width), int(landmark["y"] * height)

    @staticmethod
    def _draw_centered_text(frame, text: str, center_x: int, y: int):
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        color = (255, 255, 255)

        text_width, text_height = cv2.getTextSize(text, font, font_scale, thickness)[0]
        x = center_x - text_width // 2

        cv2.putText(frame, text, (x, y), font, font_scale, color, thickness)

    def _draw_landmarks(self, frame, landmarks: PlayerLandmarks):
        height, width, _ = frame.shape

        for landmark_id, landmark in landmarks.items():
            x, y = self._to_pixel(landmark, width, height)
            if 0 <= x < width and 0 <= y < height:
                cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
                cv2.putText(
                    frame,
                    str(landmark_id),
                    (x + 5, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (0, 255, 255),
                    1,
                )

        for start_id, end_id in self.CONNECTIONS:
            if start_id not in landmarks or end_id not in landmarks:
                continue

            start = self._to_pixel(landmarks[start_id], width, height)
            end = self._to_pixel(landmarks[end_id], width, height)
            cv2.line(frame, start, end, (255, 255, 255), 2)
