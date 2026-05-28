# 컴퓨터 비전 게임 프로젝트 대화 정리

정리 날짜: 2026년 5월 28일

## 1. 프로젝트 개요

카메라 기반 실시간 전신 모션 인식 레이싱 아케이드 게임을 만든다.

두 명의 플레이어가 카메라 앞에서 화면에 제시된 목표 동작을 따라 한다. 동작에 성공하면 캐릭터가 가속하고, 먼저 결승선에 도달한 플레이어가 승리한다.

핵심 재미 요소는 다음과 같다.

- 빠른 반응 속도 경쟁
- 콤보 유지로 속도를 높이는 긴장감
- 콤보가 끊겨 감속 중일 때 다시 동작을 맞춰 속도를 보존하는 Recovery 쾌감

## 2. 화면 구조

Pygame 기반으로 제작할 예정이다.

전체 화면은 `1 : 2 : 1` 비율로 나눈다.

- 왼쪽 영역: Player 1 레이싱 트랙
- 중앙 영역: 목표 모션 + 카메라 화면
- 오른쪽 영역: Player 2 레이싱 트랙

중앙 영역은 다시 상하 2분할, 좌우 2분할한다.

- 중앙 상단: `P1 Target | P2 Target`
- 중앙 하단: `P1 Cam | P2 Cam`

## 3. 현재 인식 방식

MediaPipe Pose를 사용한다.

처음에는 얼굴과 손가락 랜드마크를 사용하지 않는다.

현재 사용하는 랜드마크:

- `11, 12`: 어깨
- `13, 14`: 팔꿈치
- `15, 16`: 손목
- `23, 24`: 골반
- `25, 26`: 무릎
- `27, 28`: 발목
- `29, 30`: 뒤꿈치
- `31, 32`: 발끝

손가락 랜드마크 `17~22`는 흔들림이 심할 수 있어서 제외했다.

랜드마크 떨림은 EMA smoothing 방식으로 완화한다.

## 4. 코드 구조 방향

전체 구조는 다음 흐름을 기준으로 한다.

```text
PoseConnector
-> PoseDetector
-> Camera
```

그리고 포즈 판정은 다음 흐름을 목표로 한다.

```text
PoseConnector
-> PoseDetector.process_frame()
-> landmarks_by_player 받기
-> PoseLibrary에서 rule 받기
-> Player 1, Player 2 각각 성공 여부 판단
```

책임 분리는 다음과 같다.

- `Camera`: 카메라 열기, 원본 프레임 읽기, 카메라 닫기
- `PoseDetector`: MediaPipe 실행, 랜드마크 추출, smoothing, 화면 표시용 점/선 그리기
- `PoseLibrary`: 포즈 목록과 포즈 판정 rule 관리
- `PoseConnector`: 이후 만들 예정. detector와 library를 연결해 플레이어별 성공 여부를 반환
- `PlayerState`: 이후 만들 예정. 속도, 콤보, 감속, Recovery, 남은 거리 계산
- `Renderer`: 이후 만들 예정. RenderData를 받아 Pygame 화면 출력

## 5. 현재 만든 파일

현재까지 새로 만든 파일은 다음 3개다.

- `camera.py`
- `pose_detector.py`
- `pose_library.py`

기존 파일:

- `RACE.py`: 기존 MediaPipe 테스트 코드
- `pose_landmarker_lite.task`
- `pose_landmarker_full.task`
- `pose_landmarker_heavy.task`

## 6. camera.py

`Camera` 클래스는 노트북 카메라에서 원본 프레임을 가져오는 역할만 한다.

중요한 결정:

- 좌우반전은 `Camera`에서 하지 않는다.
- 프레임 위에 무언가를 그리는 작업도 `Camera`에서 하지 않는다.
- `Camera`는 이미지 공급자 역할만 한다.

주요 함수:

- `__init__(camera_index=0, width=1280, height=720)`
  - 카메라 번호, 프레임 너비, 높이를 저장한다.

- `open()`
  - OpenCV의 `cv2.VideoCapture()`로 카메라를 연다.
  - 이미 열려 있으면 다시 열지 않는다.
  - 카메라를 열 수 없으면 `RuntimeError`를 발생시킨다.

- `get_frame()`
  - 카메라에서 프레임 한 장을 읽어온다.
  - 카메라가 아직 열려 있지 않으면 내부에서 `open()`을 먼저 호출한다.
  - 프레임을 읽지 못하면 `None`을 반환한다.
  - 좌우반전 없이 원본 프레임을 반환한다.

- `is_opened()`
  - 카메라가 열려 있는지 확인한다.

- `close()`
  - 카메라를 release하고 내부 상태를 정리한다.

## 7. pose_detector.py

`PoseDetector`는 카메라 프레임에서 사람의 랜드마크를 추출하고, 표시용 프레임에 점과 선을 그린다.

### PoseDetectorConfig

설정값을 담는 dataclass다.

값:

- `model_path`: MediaPipe 모델 파일 경로. 기본값은 `pose_landmarker_heavy.task`
- `max_players`: 최대 인식 인원. 기본값은 `2`
- `smoothing_alpha`: EMA smoothing 강도. 기본값은 `0.35`
- `fps`: MediaPipe timestamp 계산용 FPS. 기본값은 `30`

`@dataclass(frozen=True)`를 사용한다.

- `@dataclass`: 설정값 저장용 클래스를 간단히 만들기 위해 사용
- `frozen=True`: 생성 후 설정값이 실수로 바뀌지 않게 막기 위해 사용

### LandmarkSmoother

랜드마크 좌표의 떨림을 줄이는 클래스다.

EMA 방식:

```text
보정 좌표 = 이전 좌표 * (1 - alpha) + 현재 좌표 * alpha
```

주요 함수:

- `smooth_landmark(player_id, landmark_id, landmark)`
  - 랜드마크 하나를 smoothing한다.
  - 반환값은 `x`, `y`, `z`, `visibility`, `presence`를 가진 dictionary다.

- `smooth_pose(player_id, pose_landmarks, tracked_ids)`
  - 한 사람의 여러 랜드마크를 smoothing한다.
  - 현재 추적하는 랜드마크만 골라서 반환한다.

### PoseDetector

핵심 클래스다.

현재 추적 랜드마크:

```python
[11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
```

주요 함수:

- `__init__(config=None, camera=None)`
  - 설정값 저장
  - Camera 객체 저장
  - LandmarkSmoother 생성
  - MediaPipe PoseLandmarker 생성

- `process_frame(frame=None)`
  - 핵심 함수다.
  - `frame`이 없으면 연결된 `Camera`에서 프레임을 가져온다.
  - `frame`이 있으면 전달받은 프레임을 그대로 사용한다.
  - `draw_player_areas()`를 통해 좌우반전과 P1/P2 영역 표시를 한다.
  - BGR 이미지를 RGB로 바꿔 MediaPipe에 넣는다.
  - 사람들을 감지하고 x좌표 기준으로 정렬한다.
  - 왼쪽 사람을 Player 1, 오른쪽 사람을 Player 2로 본다.
  - 필요한 랜드마크만 추출하고 smoothing한다.
  - `_draw_landmarks()`로 점과 선을 그린다.
  - `drawn_frame, landmarks_by_player`를 반환한다.

- `draw_player_areas(frame)`
  - 프레임을 좌우반전한다.
  - 중앙 세로선을 그린다.
  - 왼쪽 아래 중앙에 `Player 1`을 표시한다.
  - 오른쪽 아래 중앙에 `Player 2`를 표시한다.
  - 수정된 프레임을 반환한다.

- `close()`
  - MediaPipe landmarker를 닫는다.
  - 연결된 Camera가 있으면 Camera도 닫는다.

- `_get_pose_center_x(pose_landmarks)`
  - 사람의 중심 x좌표를 계산한다.
  - 어깨와 골반 좌표 `11, 12, 23, 24`를 기준으로 한다.

- `_to_pixel(landmark, width, height)`
  - MediaPipe의 `0.0~1.0` 정규화 좌표를 실제 픽셀 좌표로 바꾼다.

- `_draw_centered_text(frame, text, center_x, y)`
  - 텍스트를 특정 x좌표 기준으로 가운데 정렬해서 그린다.

- `_draw_landmarks(frame, landmarks)`
  - 랜드마크 점과 연결선을 그린다.
  - 점은 초록색, 선은 흰색으로 표시한다.

`process_frame()` 반환값 예시:

```python
drawn_frame, landmarks_by_player = detector.process_frame()
```

`landmarks_by_player` 구조:

```python
{
    0: {
        11: {"x": 0.4, "y": 0.3, "z": -0.1, "visibility": 0.9, "presence": 0.9},
        12: {...},
    },
    1: {
        11: {...},
        12: {...},
    },
}
```

여기서 `0`은 Player 1, `1`은 Player 2다.

## 8. pose_library.py

`PoseLibrary`는 포즈 rule을 관리하고, 랜드마크가 특정 포즈를 만족하는지 판단한다.

### PoseTolerance

포즈 판정 허용 오차를 저장한다.

각도, 거리, 위치는 단위가 다르기 때문에 하나의 값으로 합치지 않고 따로 둔다.

기본값:

```python
PoseTolerance(
    angle=25.0,
    distance=0.25,
    position=0.08,
)
```

### PoseRule

포즈 하나의 정보를 담는다.

값:

- `name`: 포즈 이름
- `difficulty`: 난이도
- `checker`: 실제 판정 함수

함수:

- `check(landmarks)`
  - 랜드마크가 없으면 `False`
  - 있으면 연결된 판정 함수를 실행한다.

### PoseLibrary

포즈 rule 목록을 관리한다.

현재 등록된 포즈:

- `x_arms`: 팔을 X자로 교차하는 포즈

주요 함수:

- `__init__(tolerance=None)`
  - 허용 오차를 저장한다.
  - 포즈 rule 목록을 만든다.

- `get_random_rule(max_difficulty=None)`
  - 등록된 포즈 rule 중 하나를 무작위로 반환한다.
  - `max_difficulty`가 있으면 해당 난이도 이하의 rule만 후보로 사용한다.

- `is_x_arms_pose(landmarks)`
  - X자 팔 포즈인지 판정한다.

X자 팔 포즈 조건:

```text
1. 왼쪽 팔꿈치-왼쪽 손목 선이 수평선과 약 45도
2. 오른쪽 팔꿈치-오른쪽 손목 선이 수평선과 약 45도
3. 왼손목 x > 오른손목 x
```

이 조건은 너무 빡빡하게 잡지 않고, 게임에서 자연스럽게 성공할 수 있도록 완화한 기준이다.

보조 함수:

- `_angle_close_to(angle, target)`
  - 현재 각도가 목표 각도와 허용 오차 안에 있는지 확인한다.

- `_has_landmarks(landmarks, required_ids)`
  - 필요한 랜드마크가 모두 있는지 확인한다.

- `_line_angle(start, end)`
  - 두 랜드마크를 잇는 선의 각도를 계산한다.

## 9. 포즈 판정 설계 기준

포즈 판정은 절대 좌표만으로 하지 않는다.

주로 다음 기준을 조합한다.

- 관절 각도
- 랜드마크 간 위치 관계
- 랜드마크 간 정규화 거리

초기 구현에서는 z축을 사용하지 않는다.

이유:

- MediaPipe의 z값은 실제 거리 단위가 아니다.
- 웹캠 환경에서 조명, 몸 회전, 카메라 각도에 따라 흔들릴 수 있다.
- 현재 필요한 포즈는 x, y 기준으로도 충분히 판정 가능하다.

z축은 나중에 손을 앞으로 내미는 동작처럼 깊이 정보가 꼭 필요한 포즈가 생기면 보조 조건으로 추가한다.

포즈 rule은 처음부터 너무 엄격하게 만들지 않는다.

이유:

- 플레이어는 화면에 제시된 목표 포즈를 보고 따라 한다.
- 완전히 이상한 포즈로 성공하는 경우는 많지 않을 것이다.
- 게임에서는 빠른 성공 피드백이 중요하다.
- 테스트 후 오인식이 잦은 포즈만 조건을 보강한다.

## 10. 현재 작동 흐름

현재까지 만든 코드 기준 작동 흐름:

```text
1. Camera가 카메라에서 원본 프레임을 가져온다.
2. PoseDetector가 프레임을 받는다.
3. PoseDetector가 프레임을 좌우반전하고 P1/P2 영역을 표시한다.
4. MediaPipe가 사람의 랜드마크를 찾는다.
5. 사람들을 왼쪽부터 Player 1, Player 2로 정렬한다.
6. 필요한 랜드마크만 추출한다.
7. 랜드마크 좌표를 smoothing한다.
8. 프레임에 점과 선을 그린다.
9. PoseLibrary의 rule이 랜드마크를 받아 포즈 성공 여부를 판단한다.
```

## 11. 다음 작업 예정

다음에 만들 클래스는 `PoseConnector`다.

예상 역할:

```text
PoseDetector.process_frame() 호출
-> drawn_frame, landmarks_by_player 받기
-> PoseLibrary에서 현재 포즈 rule 받기
-> Player 1, Player 2 각각 rule.check() 실행
-> 두 플레이어의 성공 여부 반환
```

오늘 목표로 잡았던 흐름:

```text
카메라로 사람 촬영
-> PoseDetector가 랜드마크 추출
-> PoseConnector에 랜드마크 전달
-> 임시 동작과 비교
-> 맞는지/아닌지 출력
```

## 12. Notion에 정리한 내용

Notion의 `컴비 플젝 게임 기획` 페이지와 그 하위 `코드 구조` 페이지를 읽었다.

이후 `컴비 플젝 게임 기획` 하위에 다음 페이지를 만들었다.

- `2026년 5월 26일 포즈 규칙`

내용:

- 포즈 판정 기준
- 관절 각도
- 위치 관계
- 정규화 거리
- 허용 오차
- z축 사용 여부
- X자 팔 포즈 예시

`코드 구조` 하위에 클래스 정리 페이지를 만들려 했지만, Notion 요청이 오래 걸려 중단되었다. 이후 사용자가 Notion 검색을 끊으라고 해서 더 진행하지 않았다.

## 13. 중요 결정 요약

- 카메라 좌우반전은 `Camera`가 아니라 `PoseDetector.draw_player_areas()`에서 한다.
- `Camera`는 원본 프레임만 반환한다.
- `PoseDetector.process_frame()` 하나로 카메라 프레임 처리와 외부 프레임 처리를 모두 담당한다.
- `process_camera_frame()`은 제거했다.
- Player 1/2 구분은 사람 중심 x좌표 기준으로 한다.
- 왼쪽 사람은 Player 1, 오른쪽 사람은 Player 2다.
- 얼굴과 손가락 랜드마크는 제외한다.
- 초기 포즈 판정은 x, y 좌표만 사용한다.
- z축은 나중에 필요할 때만 추가한다.
- 포즈 rule은 느슨하게 시작하고, 테스트 후 필요한 조건만 보강한다.
