from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Dict, List

from pose_detector import PlayerLandmarks


@dataclass(frozen=True)
class PoseTolerance:
    angle: float = 25.0
    distance: float = 0.25
    position: float = 0.08


@dataclass(frozen=True)
class PoseRule:
    name: str
    difficulty: int
    checker: Callable[[PlayerLandmarks], bool]

    def check(self, landmarks: PlayerLandmarks | None) -> bool:
        if not landmarks:
            return False
        return self.checker(landmarks)


class PoseLibrary:
    def __init__(self, tolerance: PoseTolerance | None = None):
        self.tolerance = tolerance or PoseTolerance()
        self.rules: List[PoseRule] = [
            PoseRule(
                name="x_arms",
                difficulty=1,
                checker=self.is_x_arms_pose,
            )
        ]

    def get_random_rule(self, max_difficulty: int | None = None) -> PoseRule:
        candidates = self.rules
        if max_difficulty is not None:
            candidates = [rule for rule in self.rules if rule.difficulty <= max_difficulty]

        if not candidates:
            raise ValueError("선택 가능한 포즈 rule이 없습니다.")

        return random.choice(candidates)

    def is_x_arms_pose(self, landmarks: PlayerLandmarks) -> bool:
        required_ids = [13, 14, 15, 16]
        if not self._has_landmarks(landmarks, required_ids):
            return False

        left_angle = self._line_angle(landmarks[13], landmarks[15])
        right_angle = self._line_angle(landmarks[14], landmarks[16])

        left_is_diagonal = self._compare_angle(abs(left_angle), 45.0)
        right_is_diagonal = self._compare_angle(abs(right_angle), 45.0)
        wrists_are_crossed = landmarks[15]["x"] > landmarks[16]["x"]

        return left_is_diagonal and right_is_diagonal and wrists_are_crossed

    def _compare_angle(self, angle: float, target: float) -> bool:
        return abs(angle - target) <= self.tolerance.angle

    @staticmethod
    def _has_landmarks(landmarks: PlayerLandmarks, required_ids: List[int]) -> bool:
        return all(landmark_id in landmarks for landmark_id in required_ids)

    @staticmethod
    def _line_angle(start: Dict[str, float], end: Dict[str, float]) -> float:
        dx = end["x"] - start["x"]
        dy = end["y"] - start["y"]
        return math.degrees(math.atan2(dy, dx))
