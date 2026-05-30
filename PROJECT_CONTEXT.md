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

## 14. 2026년 5월 28일 작업 정리

### PoseConnector 설계

`pose_connector.py`를 새로 만들었다.

역할:

```text
PoseConnector
-> PoseDetector.process_frame() 호출
-> drawn_frame, landmarks_by_player 받기
-> PoseLibrary에서 플레이어별 PoseRule 가져오기
-> 각 플레이어의 현재 랜드마크와 자기 PoseRule 비교
-> 성공 여부, drawn_frame, pose_rules_by_player 반환
```

중요 결정:

- 두 플레이어가 같은 포즈를 따라 하는 구조가 아니다.
- Player 1, Player 2가 각각 다른 목표 포즈를 가진다.
- 랜덤 선택이라 같은 포즈가 나올 수는 있다.
- 각 플레이어는 이전 프레임에서 자기 포즈를 성공했을 때만 새 포즈를 받는다.
- 처음에는 포즈 룰이 없으므로, `success_by_player`를 `{0: True, 1: True}`로 시작해서 첫 `update()`에서 룰을 받게 했다.

현재 핵심 상태:

```python
self.current_rules_by_player = {
    0: None,
    1: None,
}

self.success_by_player = {
    0: True,
    1: True,
}
```

`update()` 반환값은 `PoseConnectorResult` dataclass다.

```python
PoseConnectorResult(
    success_by_player=...,
    drawn_frame=...,
    pose_rules_by_player=...,
)
```

이렇게 한 이유:

- `GameManager`가 `PoseConnector.update()`를 한 번만 호출해도 된다.
- 그 결과로 렌더링 데이터도 만들고, 성공 여부도 확인할 수 있다.
- 튜플로 3개를 반환하는 것보다 필드명이 있어서 나중에 읽기 쉽다.

### Renderer 설계

`renderer.py`를 새로 만들었다.

현재는 테스트 단계라 `drawn_frame`만 OpenCV 창에 띄운다.

```text
Renderer.render(RenderData)
-> cv2.imshow()
```

`RenderData`도 만들었다.

```python
RenderData(
    drawn_frame=...,
    pose_rules_by_player=...,
)
```

중요 결정:

- `Renderer`가 `PoseConnector`나 나중에 만들 `PlayerState`를 직접 참조하지 않게 한다.
- `GameManager`가 렌더링에 필요한 데이터를 모아서 `RenderData`로 넘긴다.
- 이렇게 해야 렌더러가 게임 로직 클래스에 덜 의존한다.

### GameManager 설계

`game_manager.py`를 새로 만들었다.

현재 목표:

```text
PoseConnector.update() 호출
-> PoseConnectorResult 받기
-> RenderData 만들기
-> Renderer.render() 호출
-> success_by_player 출력
```

현재 실행 흐름:

```python
pose_result = self.pose_connector.update()
render_data = self._make_render_data(pose_result)

self.renderer.render(render_data)
print(pose_result.success_by_player)
```

`try/finally`를 사용했다.

이유:

- 게임 루프 중 에러가 나거나 `q`로 종료해도 `close()`가 실행되게 하기 위해서다.
- 카메라와 OpenCV 창은 반드시 정리해야 한다.

### 클래스 의존 관계

최종적으로 정한 관계:

```text
GameManager
-> Renderer
-> PoseConnector
   -> PoseDetector
      -> Camera
   -> PoseLibrary
```

생성 방식:

- `PoseDetector`는 `camera=None`이면 내부에서 `Camera()`를 만든다.
- `PoseConnector`는 `detector=None`, `library=None`이면 내부에서 `PoseDetector()`, `PoseLibrary()`를 만든다.
- `GameManager`는 현재 파라미터를 받지 않고 내부에서 `PoseConnector()`, `Renderer()`를 만든다.

판단:

- 지금 단계에서는 `GameManager`가 무조건 직접 생성하는 방식이 단순해서 좋다.
- 나중에 테스트가 필요하면 다시 외부 객체 주입 방식으로 바꿀 수 있다.

### KeyError 문제

런타임 중 `KeyError`가 발생했다.

원인:

초기에는 성공 여부가 다음처럼 들어 있었다.

```python
{0: True, 1: True}
```

그런데 사람이 카메라에 잡히지 않으면 `landmarks_by_player`가 `{}`가 된다.

기존 `_check_players()`는 감지된 플레이어만 결과에 넣었기 때문에, 사람이 안 잡힌 프레임에서는 결과가 `{}`가 됐다.

그 뒤 다음 프레임에서 아래 코드가 실행되면:

```python
self.success_by_player[player_id]
```

`success_by_player` 안에 `0`, `1` key가 없어서 `KeyError: 0`이 발생했다.

해결:

`_check_players()`가 항상 모든 플레이어 key를 유지하게 수정했다.

사람이 안 잡힌 플레이어는 `False`로 둔다.

```python
{
    0: False,
    1: False,
}
```

### OpenCV 창이 바로 꺼지는 문제

처음에는 `cv2.imshow()` 뒤에 아무것도 없어서 바로 꺼지는 것처럼 보일 수 있다고 생각했다.

하지만 현재 구조에서는 `Renderer.should_quit()` 안에서 `cv2.waitKey(1)`을 호출하고 있다.

```python
cv2.waitKey(1)
```

그래서 더 유력한 원인은 `KeyError`로 게임 루프가 중단되고, `finally`에서 카메라와 창이 닫힌 것이었다.

### MediaPipe 경고 로그

실행 중 다음 경고가 떴다.

```text
Feedback manager requires a model with a single signature inference.
Disabling support for feedback tensors.
```

이건 MediaPipe 내부 warning이다.

의미:

- 현재 사용하는 `.task` 모델이 MediaPipe의 feedback tensor 기능 조건과 맞지 않아서 그 기능을 끈다는 뜻이다.
- 포즈 인식 자체가 실패했다는 뜻은 아니다.
- 프로그램이 계속 실행되면 무시해도 된다.

판단:

- 지금은 신경 쓰지 않아도 된다.
- 창이 꺼지거나 프로그램이 종료된다면 이 warning보다 Python 예외나 카메라 문제를 먼저 봐야 한다.

---

## 2026-05-29 작업 정리

### 포즈 룰 작업

오늘은 `PoseLibrary`에 목표 포즈 룰을 많이 추가하고 기존 룰을 조정했다.

현재 주요 포즈 룰:

- `x_arms`
- `dab`
- `happy`
- `so_cool`
- `jojo_stand1`
- `praise_the_sun`
- `sor`
- `jojo_stand2`
- `no`
- `what`
- `jackson`

주요 변경:

- `PoseRule`에서 `difficulty`를 제거하고 `id` 기반으로 관리한다.
- `get_random_rule(rule_id=None)`는 인자가 없으면 랜덤 룰, 인자가 있으면 해당 id 룰을 반환한다.
- 머리 위치 확인을 위해 랜드마크 `0, 7, 8`을 추적 대상에 포함했다.
- 무릎/발 관련 랜드마크는 현재 룰에서 제외했다.
- 포즈 룰 작성 시 `_angles_close`, `_joint_angle`, `_line_angle` 같은 기존 보조 함수를 재사용하는 방향으로 정리했다.

### 포즈별 기준 요약

`dab`

- 두 손목이 어깨보다 위에 있어야 한다.
- 얼굴을 덮는 손목은 두 어깨 사이에 있어야 한다.
- 뻗는 손목은 어깨 바깥에 있어야 한다.
- 뻗는 팔은 어깨-팔꿈치 라인과 팔꿈치-손목 라인이 비슷해야 한다.
- 얼굴을 덮는 팔은 전체 일직선 대신, 덮는 팔꿈치-손목 각도와 뻗는 어깨-팔꿈치 각도를 비교한다.

`happy`

- 올린 팔의 팔꿈치 관절각이 약 45도이다.
- 올린 손목은 같은 방향 귀 높이와 비슷해야 한다.
- 내린 손목은 같은 방향 골반 높이와 비슷해야 한다.

`so_cool`

- 대각 팔은 팔꿈치-손목 라인이 45도 또는 135도이다.
- 수평 팔은 팔꿈치-손목 라인이 0도 또는 180도이다.
- 두 손목 높이가 비슷해야 한다.

`jojo_stand1`

- 올린 팔 손목은 코와 어깨 평균 높이 사이에 있어야 한다.
- 올린 팔의 손목-팔꿈치-어깨 관절각은 약 30도이다.
- 내린 팔의 어깨-팔꿈치 라인은 약 60도이다.
- 내린 손목은 팔꿈치보다 아래에 있어야 한다.
- 좌우 대칭 각도 문제 때문에 `min(angle, 180 - angle)` 방식으로 보정했다.

`praise_the_sun`

- 양쪽 어깨-팔꿈치 라인이 약 45도이다.
- 양팔의 어깨-팔꿈치-손목 관절각이 180도에 가까워야 한다.
- 좌우 대칭 포즈라 방향 함수는 따로 두지 않았다.

`sor`

- 올린 팔과 내린 팔로 나눈다.
- 두 팔 모두 어깨-팔꿈치-손목 관절각이 90도이다.
- 올린 손목은 팔꿈치보다 위에 있어야 한다.
- 내린 손목은 팔꿈치보다 아래에 있어야 한다.

`jojo_stand2`

- 올린 팔은 어깨-팔꿈치-손목 관절각이 90도이다.
- 올린 손목은 팔꿈치보다 위에 있어야 한다.
- 내린 손목은 팔꿈치보다 아래에 있어야 한다.
- 양쪽 팔꿈치 높이가 비슷해야 한다.
- 올린 팔꿈치는 자기 어깨보다 몸 안쪽에 있어야 한다.

`no`

- 한쪽 팔만 검사한다.
- 어깨-팔꿈치 라인이 수직에 가까워야 한다.
- 손목은 두 어깨 평균 높이 근처에 있어야 한다.
- 손목은 코보다 몸 안쪽에 있어야 한다.
- 왼손이면 오른쪽 귀, 오른손이면 왼쪽 귀의 x 위치와 비슷해야 한다.

`what`

- 올린 팔과 내린 팔로 나눈다.
- 올린 팔의 어깨가 내린 팔의 어깨보다 높아야 한다.
- 두 팔 모두 어깨-팔꿈치-손목 관절각이 180도에 가까워야 한다.
- 팔이 오른쪽 방향이면 왼손목이 아래 팔이어야 한다.
- 팔이 왼쪽 방향이면 오른손목이 아래 팔이어야 한다.

`jackson`

- 굽힌 팔과 핀 팔로 나눈다.
- 굽힌 팔꿈치는 자기 어깨보다 위에 있어야 한다.
- 굽힌 손목은 코보다 위에 있어야 한다.
- 굽힌 팔의 어깨-팔꿈치-손목 관절각은 60도이다.
- 핀 팔의 어깨-팔꿈치-손목 관절각은 180도이다.
- 핀 팔꿈치는 자기 어깨보다 바깥쪽에 있어야 한다.

### 포즈 디버깅 함수

`PoseLibrary`에 디버그용 함수를 추가했다.

```python
debug_bool_list(values: List[bool]) -> None
```

불리언 조건 리스트를 출력해서, 포즈 룰의 어떤 조건이 실패하는지 빠르게 확인하는 용도이다.

### 스켈레톤 추출 스크립트

`skeleton_extractor.py`를 추가했다.

동작:

- `image/` 폴더 안의 이미지 파일을 읽는다.
- MediaPipe로 포즈를 감지한다.
- 현재 프로젝트에서 사용하는 랜드마크만 이미지 위에 찍는다.
- `PoseDetector.CONNECTIONS` 기준으로 선을 연결한다.
- 결과 이미지를 `image_skeleton/파일명_skeleton.png`로 저장한다.

기본 실행:

```bash
python skeleton_extractor.py
```

주의:

- 실행 검증은 하지 않았다.
- `mediapipe`, `cv2`가 설치된 같은 Python 환경에서 실행해야 한다.

### PlayerState 추가

`player_state.py`를 추가했다.

플레이어의 레이스 상태를 관리한다.

주요 값:

- `total_distance = 1612.0`
- `cur_speed`
- `min_speed = 5.5`
- `max_speed = 30.0`
- `accel_value_per_suc = 4.0`
- `decel_value_per_sec = 2.0`
- `cur_pos`
- `remained_distance`
- `no_decel_time`
- `dt`

업데이트 흐름:

```text
update_dt()
-> update_speed(is_success)
-> update_distance()
```

성공 시:

- `cur_speed += 4.0`
- `no_decel_time = 2.0`

실패 시:

- `no_decel_time > 0`이면 감속하지 않고 유예 시간만 줄인다.
- 유예 시간이 끝나면 `decel_value_per_sec * dt`만큼 감속한다.

거리 계산:

- `cur_pos += cur_speed * dt`
- `remained_distance = total_distance - cur_pos`
- 결승선을 넘으면 `cur_pos`는 `total_distance`에서 멈춘다.

`PlayerState.update()`는 `PlayerStateResult`를 반환한다.

```python
PlayerStateResult(
    cur_speed=...,
    cur_pos=...,
    remained_distance=...,
)
```

### RenderData 구조 변경

렌더러에 전달하는 데이터 구조를 정리했다.

현재 `RenderData`는 다음 값을 가진다.

```python
drawn_frame
cur_speed_by_player
cur_pos_by_player
remained_distance_by_player
success_by_player
pose_rules_by_player
```

`GameManager` 흐름:

1. `PoseConnector.update()` 호출
2. 플레이어별 `PlayerState.update(success)` 호출
3. `Renderer.make_render_data(pose_result, player_state_results)` 호출
4. `Renderer.render(render_data)` 호출

### Pygame 렌더러 전환

기존 OpenCV 렌더러를 Pygame 렌더러로 교체했다.

이유:

- OpenCV는 카메라 확인에는 좋지만 게임 UI를 만들기 불편하다.
- Pygame은 텍스트, 패널, 진행도, 사운드, 성공 이펙트 구현이 더 쉽다.

`PoseDetector`는 이제 중앙선과 플레이어 라벨을 그리지 않는다.

현재 `PoseDetector.draw_player_areas()`는 카메라 프레임을 좌우반전해서 반환하는 역할만 한다.

UI는 전부 `Renderer`가 담당한다.

현재 Pygame UI:

- 전체화면 카메라 프레임
- 중앙 분리선
- 플레이어별 얇은 반투명 테두리
- 좌상단 목표 포즈 카드
- 목표 포즈 카드에는 현재 목표 포즈 이름 표시
- 왼쪽 아래 상태 패널
- 상태 패널 위 왼쪽에 `PLAYER 1`, `PLAYER 2`
- 상태 패널 안에 `SPEED`, 현재 속도, 현재 위치 / 전체 거리 표시
- 오른쪽에는 `START`와 `FINISH`가 있는 수직 진행 트랙
- 진행 트랙 위에 현재 위치 마커 표시

### 성공 피드백

성공 시 피드백을 추가했다.

성공 플래시:

- 성공한 플레이어 화면 테두리가 초록색으로 빛난다.
- 약 0.35초 동안 서서히 사라진다.

성공 사운드:

- `sound/correct_player1.mp3`
- `sound/correct_player2.mp3`

플레이어 1 성공 시 `correct_player1.mp3`를 재생한다.

플레이어 2 성공 시 `correct_player2.mp3`를 재생한다.

사운드 파일이 없거나 로딩 실패하면 해당 플레이어는 무음으로 넘어간다.

### 연속 성공 필터

연속 성공이 발생하는 문제가 있었다.

원인 후보:

- 같은 포즈가 랜덤으로 연속 등장할 수 있다.
- 룰이 바뀐 직후에도 같은 프레임에서 바로 성공 검사가 된다.
- 포즈 룰의 tolerance가 넓고, 일부 포즈 조건이 서로 겹친다.
- MediaPipe 스무딩 때문에 이전 프레임 자세가 잠깐 남을 수 있다.

해결:

`PoseConnector` 안에서 성공 이벤트를 필터링한다.

현재 기준:

```text
현재 raw True, 이전 filtered False -> True
현재 raw True, 이전 filtered True  -> False
```

즉 한 프레임 성공하면 다음 프레임은 raw 성공이어도 무조건 실패로 반환한다.

이 필터링은 `GameManager`가 아니라 `PoseConnector`에서 처리한다.

### 화면 구성 관련 판단

노트북 카메라로 상체와 팔을 모두 잡으려면 사람이 멀리 서야 하고, 그 결과 화면에서 사람이 작게 보인다.

따라서 실제 사람 이미지를 크게 보이게 하는 것보다:

- 카메라 화면을 전체화면으로 사용
- 스켈레톤 선을 잘 보이게 표시
- UI는 반투명 패널로 정리

하는 방향이 더 낫다고 판단했다.

Pygame에서 실제 화면 크기를 읽어 UI를 배치한다.

```python
self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
self.window_width, self.window_height = self.screen.get_size()
```

### 남은 개선 후보

- 목표 포즈 이름 대신 스켈레톤 이미지나 흰 아바타 이미지를 표시하기
- 같은 포즈가 연속으로 뽑히지 않도록 `get_random_rule()` 개선하기
- 새 포즈가 나온 직후 0.3초 정도 성공 판정을 막는 grace time 추가하기
- 결승선 도착 시 승리 화면 추가하기
- 진행도 트랙에 플레이어별 색상 다르게 주기
- 상태 패널과 목표 포즈 카드 디자인 더 다듬기
- 사운드 재생이 겹칠 때 볼륨/쿨다운 조정하기
