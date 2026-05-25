import cv2
import time
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class LandmarkSmoother:
    def __init__(self, alpha=0.35):
        self.alpha = alpha
        self.previous = {}

    def smooth_landmark(self, player_id, landmark_id, landmark):
        key = (player_id, landmark_id)

        current = {
            "x": landmark.x,
            "y": landmark.y,
            "z": landmark.z,
            "visibility": landmark.visibility,
            "presence": landmark.presence,
        }

        if key not in self.previous:
            self.previous[key] = current
            return current

        prev = self.previous[key]

        smoothed = {
            "x": prev["x"] * (1 - self.alpha) + current["x"] * self.alpha,
            "y": prev["y"] * (1 - self.alpha) + current["y"] * self.alpha,
            "z": prev["z"] * (1 - self.alpha) + current["z"] * self.alpha,
            "visibility": current["visibility"],
            "presence": current["presence"],
        }

        self.previous[key] = smoothed
        return smoothed

    def smooth_pose(self, player_id, pose_landmarks, tracked_ids):
        result = {}

        for landmark_id in tracked_ids:
            landmark = pose_landmarks[landmark_id]
            result[landmark_id] = self.smooth_landmark(
                player_id,
                landmark_id,
                landmark
            )

        return result
# =========================
# 설정
# =========================

MODEL_PATH = "pose_landmarker_heavy.task"
CAMERA_INDEX = 0
MAX_PLAYERS = 2

TRACKED_LANDMARKS = list(range(11, 23))
SMOOTHING_ALPHA = 0.35

smoother = LandmarkSmoother(alpha=SMOOTHING_ALPHA)
# =========================
# MediaPipe 초기화
# =========================

base_options = python.BaseOptions(model_asset_path=MODEL_PATH)

options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_poses=MAX_PLAYERS,
    min_pose_detection_confidence=0.5,
    min_pose_presence_confidence=0.5,
    min_tracking_confidence=0.5,
)

landmarker = vision.PoseLandmarker.create_from_options(options)


# =========================
# 그리기용 연결선
# =========================

ARM_CONNECTIONS = [
    # 몸통
    (11, 12),  # left shoulder - right shoulder
    

    # 왼팔
    (11, 13),  # left shoulder - left elbow
    (13, 15),  # left elbow - left wrist
    (15, 17),  # left wrist - left pinky
    (15, 19),  # left wrist - left index
    (15, 21),  # left wrist - left thumb

    # 오른팔
    (12, 14),  # right shoulder - right elbow
    (14, 16),  # right elbow - right wrist
    (16, 18),  # right wrist - right pinky
    (16, 20),  # right wrist - right index
    (16, 22),  # right wrist - right thumb

]


# =========================
# 유틸 함수
# =========================

def smoothed_to_pixel(smoothed_landmark, width, height):
    x = int(smoothed_landmark["x"] * width)
    y = int(smoothed_landmark["y"] * height)
    return x, y


def get_pose_center_x(pose_landmarks):
    """
    사람을 Player 1 / Player 2로 나누기 위해
    몸 중심의 x좌표를 계산.
    어깨와 골반 중심을 기준으로 함.
    """
    key_indices = [11, 12, 23, 24]  # shoulders, hips
    xs = [pose_landmarks[i].x for i in key_indices]
    return sum(xs) / len(xs)


def extract_arm_points(pose_landmarks, width, height):
    """
    팔 판정에 필요한 주요 좌표만 뽑기.
    """
    points = {
        "left_shoulder": smoothed_to_pixel(pose_landmarks[11], width, height),
        "left_elbow": smoothed_to_pixel(pose_landmarks[13], width, height),
        "left_wrist": smoothed_to_pixel(pose_landmarks[15], width, height),

        "right_shoulder": smoothed_to_pixel(pose_landmarks[12], width, height),
        "right_elbow": smoothed_to_pixel(pose_landmarks[14], width, height),
        "right_wrist": smoothed_to_pixel(pose_landmarks[16], width, height),
    }

    return points


def draw_tracked_landmarks(frame, smoothed_landmarks):
    height, width, _ = frame.shape

    for landmark_id, landmark in smoothed_landmarks.items():
        x, y = smoothed_to_pixel(landmark, width, height)

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

    for start_id, end_id in ARM_CONNECTIONS:
        if start_id not in smoothed_landmarks or end_id not in smoothed_landmarks:
            continue

        x1, y1 = smoothed_to_pixel(smoothed_landmarks[start_id], width, height)
        x2, y2 = smoothed_to_pixel(smoothed_landmarks[end_id], width, height)

        cv2.line(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)



# =========================
# 메인 루프
# =========================

cap = cv2.VideoCapture(CAMERA_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

if not cap.isOpened():
    raise RuntimeError("카메라를 열 수 없습니다.")

frame_index = 0
fps = 30

while True:
    success, frame = cap.read()

    if not success:
        print("프레임을 읽을 수 없습니다.")
        break

    frame = cv2.flip(frame, 1)  # 거울 모드
    height, width, _ = frame.shape

    # OpenCV는 BGR, MediaPipe는 RGB 사용
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb_frame,
    )

    timestamp_ms = int(frame_index * 1000 / fps)
    frame_index += 1

    result = landmarker.detect_for_video(mp_image, timestamp_ms)

    poses = result.pose_landmarks

    if poses:
        # 왼쪽 사람을 Player 1, 오른쪽 사람을 Player 2로 정렬
        sorted_poses = sorted(poses, key=get_pose_center_x)

        for i, pose_landmarks in enumerate(sorted_poses):
            player_name = f"Player {i + 1}"

            smoothed_landmarks = smoother.smooth_pose(
            player_id=i,
            pose_landmarks=pose_landmarks,
            tracked_ids=TRACKED_LANDMARKS
            )

            draw_tracked_landmarks(frame, smoothed_landmarks)
    
    height, width, _ = frame.shape

    # 중앙선
    cv2.line(
        frame,
        (width // 2, 0),
        (width // 2, height),
        (0, 0, 255),
        2
    )

    # 좌우 플레이어 영역 표시
    cv2.putText(
        frame,
        "P1 Area",
        (30, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        "P2 Area",
        (width - 180, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2
    )

    cv2.imshow("MediaPipe Pose - 2 Players", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
landmarker.close()