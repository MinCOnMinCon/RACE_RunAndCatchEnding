from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import cv2

from pose_library import PoseRule


@dataclass(frozen=True)
class RenderData:
    drawn_frame: object
    pose_rules_by_player: Dict[int, PoseRule | None]


class Renderer:
    def __init__(self, window_name: str = "RACE"):
        self.window_name = window_name

    def render(self, data: RenderData):
        if data.drawn_frame is None:
            return

        cv2.imshow(self.window_name, data.drawn_frame)

    def should_quit(self) -> bool:
        return cv2.waitKey(1) & 0xFF == ord("q")

    def close(self):
        cv2.destroyAllWindows()
