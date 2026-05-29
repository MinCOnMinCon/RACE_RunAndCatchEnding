from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from pose_detector import PoseDetector


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def read_image(path: Path):
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def write_image(path: Path, image) -> None:
    success, encoded = cv2.imencode(path.suffix, image)
    if not success:
        raise RuntimeError(f"이미지 저장 인코딩 실패: {path}")
    encoded.tofile(path)


def iter_image_paths(input_dir: Path) -> Iterable[Path]:
    for path in sorted(input_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def to_pixel(landmark, width: int, height: int) -> tuple[int, int]:
    return int(landmark.x * width), int(landmark.y * height)


def draw_skeleton(image, pose_landmarks) -> None:
    height, width, _ = image.shape
    tracked_landmarks = PoseDetector.TRACKED_LANDMARKS
    tracked_set = set(tracked_landmarks)

    line_thickness = max(2, width // 300)
    circle_radius = max(4, width // 250)

    for start_id, end_id in PoseDetector.CONNECTIONS:
        if start_id not in tracked_set or end_id not in tracked_set:
            continue

        start = to_pixel(pose_landmarks[start_id], width, height)
        end = to_pixel(pose_landmarks[end_id], width, height)
        cv2.line(image, start, end, (255, 255, 255), line_thickness)

    for landmark_id in tracked_landmarks:
        landmark = pose_landmarks[landmark_id]
        x, y = to_pixel(landmark, width, height)
        if 0 <= x < width and 0 <= y < height:
            cv2.circle(image, (x, y), circle_radius, (0, 255, 0), -1)
            cv2.putText(
                image,
                str(landmark_id),
                (x + circle_radius, y - circle_radius),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 255),
                1,
            )


def extract_skeletons(input_dir: Path, output_dir: Path, model_path: Path) -> None:
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    base_options = python.BaseOptions(model_asset_path=str(model_path))
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        for input_path in iter_image_paths(input_dir):
            image = read_image(input_path)
            if image is None:
                print(f"읽기 실패: {input_path}")
                continue

            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
            result = landmarker.detect(mp_image)

            if result.pose_landmarks:
                draw_skeleton(image, result.pose_landmarks[0])
            else:
                print(f"포즈 감지 실패: {input_path.name}")

            output_path = output_dir / f"{input_path.stem}_skeleton.png"
            write_image(output_path, image)
            print(f"저장 완료: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="image")
    parser.add_argument("--output-dir", default="image_skeleton")
    parser.add_argument("--model", default="pose_landmarker_heavy.task")
    args = parser.parse_args()

    extract_skeletons(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        model_path=Path(args.model),
    )


if __name__ == "__main__":
    main()
