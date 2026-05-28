import cv2


class Camera:
    def __init__(
        self,
        camera_index: int = 0,
        width: int = 1280,
        height: int = 720,
    ):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cap = None

    def open(self):
        if self.is_opened():
            return

        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        if not self.cap.isOpened():
            self.cap.release()
            self.cap = None
            raise RuntimeError("카메라를 열 수 없습니다.")

    def get_frame(self):
        if not self.is_opened():
            self.open()

        success, frame = self.cap.read()
        if not success:
            return None

        return frame

    def is_opened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def close(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
