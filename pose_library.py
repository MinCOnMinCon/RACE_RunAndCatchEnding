from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Dict, List

from pose_detector import PlayerLandmarks


@dataclass(frozen=True)
class PoseTolerance:
    angle: float = 20.0
    distance: float = 0.25
    position: float = 0.08


@dataclass(frozen=True)
class PoseRule:
    id: int
    name: str
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
                id=0,
                name="x_arms",
                checker=self.is_x_arms_pose,
            ),
            PoseRule(
                id=1,
                name="dab",
                checker=self.is_dab_pose,
            ),
            PoseRule(
                id=2,
                name="happy",
                checker=self.is_happy_pose,
            ),
            PoseRule(
                id=3,
                name="so_cool",
                checker=self.is_so_cool_pose,
            ),
            PoseRule(
                id=4,
                name="jojo_stand1",
                checker=self.is_jojo_stand1_pose,
            ),
            PoseRule(
                id=5,
                name="praise_the_sun",
                checker=self.is_praise_the_sun_pose,
            ),
            PoseRule(
                id=6,
                name="sor",
                checker=self.is_sor_pose,
            ),
            PoseRule(
                id=7,
                name="jojo_stand2",
                checker=self.is_jojo_stand2_pose,
            ),
            PoseRule(
                id=8,
                name="no",
                checker=self.is_no_pose,
            ),
            PoseRule(
                id=9,
                name="what",
                checker=self.is_what_pose,
            ),
            PoseRule(
                id=10,
                name="jackson",
                checker=self.is_jackson_pose,
            ),
        ]

    def get_random_rule(self, rule_id: int | None = None) -> PoseRule:
        if not self.rules:
            raise ValueError("선택 가능한 포즈 rule이 없습니다.")

        if rule_id is not None:
            for rule in self.rules:
                if rule.id == rule_id:
                    return rule
            raise ValueError(f"id가 {rule_id}인 포즈 rule이 없습니다.")

        return random.choice(self.rules)

    def is_x_arms_pose(self, landmarks: PlayerLandmarks) -> bool:
        required_ids = [13, 14, 15, 16]
        if not self._has_landmarks(landmarks, required_ids):
            return False

        left_angle = self._line_angle(landmarks[13], landmarks[15])
        right_angle = self._line_angle(landmarks[14], landmarks[16])

        left_is_diagonal = self._angles_close(abs(left_angle), 45.0)
        right_is_diagonal = self._angles_close(abs(right_angle), 135.0)
        wrists_are_crossed = landmarks[15]["x"] > landmarks[16]["x"]

        return left_is_diagonal and right_is_diagonal and wrists_are_crossed

    def is_dab_pose(self, landmarks: PlayerLandmarks) -> bool:
        required_ids = [11, 12, 13, 14, 15, 16]
        if not self._has_landmarks(landmarks, required_ids):
            return False

        return self._is_dab_direction(
            landmarks=landmarks,
            extended_shoulder_id=11,
            extended_wrist_id=15,
            cover_elbow_id=14,
            cover_wrist_id=16,
            direction=-1,
        ) or self._is_dab_direction(
            landmarks=landmarks,
            extended_shoulder_id=12,
            extended_wrist_id=16,
            cover_elbow_id=13,
            cover_wrist_id=15,
            direction=1,
        )

    def is_happy_pose(self, landmarks: PlayerLandmarks) -> bool:
        required_ids = [7, 8, 11, 12, 13, 14, 15, 16, 23, 24]
        if not self._has_landmarks(landmarks, required_ids):
            return False

        return self._is_happy_direction(
            landmarks=landmarks,
            up_ear_id=7,
            up_shoulder_id=11,
            up_elbow_id=13,
            up_wrist_id=15,
            down_shoulder_id=12,
            down_elbow_id=14,
            down_wrist_id=16,
            down_hip_id=24,
        ) or self._is_happy_direction(
            landmarks=landmarks,
            up_ear_id=8,
            up_shoulder_id=12,
            up_elbow_id=14,
            up_wrist_id=16,
            down_shoulder_id=11,
            down_elbow_id=13,
            down_wrist_id=15,
            down_hip_id=23,
        )

    def is_so_cool_pose(self, landmarks: PlayerLandmarks) -> bool:
        required_ids = [13, 14, 15, 16]
        if not self._has_landmarks(landmarks, required_ids):
            return False

        return self._is_so_cool_direction(
            landmarks=landmarks,
            diagonal_elbow_id=13,
            diagonal_wrist_id=15,
            horizontal_elbow_id=14,
            horizontal_wrist_id=16,
        ) or self._is_so_cool_direction(
            landmarks=landmarks,
            diagonal_elbow_id=14,
            diagonal_wrist_id=16,
            horizontal_elbow_id=13,
            horizontal_wrist_id=15,
        )

    def is_jojo_stand1_pose(self, landmarks: PlayerLandmarks) -> bool:
        required_ids = [0, 11, 12, 13, 14, 15, 16]
        if not self._has_landmarks(landmarks, required_ids):
            return False

        return self._is_jojo_stand1_direction(
            landmarks=landmarks,
            up_shoulder_id=11,
            up_elbow_id=13,
            up_wrist_id=15,
            down_shoulder_id=12,
            down_elbow_id=14,
            down_wrist_id=16,
        ) or self._is_jojo_stand1_direction(
            landmarks=landmarks,
            up_shoulder_id=12,
            up_elbow_id=14,
            up_wrist_id=16,
            down_shoulder_id=11,
            down_elbow_id=13,
            down_wrist_id=15,
        )

    def is_praise_the_sun_pose(self, landmarks: PlayerLandmarks) -> bool:
        required_ids = [11, 12, 13, 14, 15, 16]
        if not self._has_landmarks(landmarks, required_ids):
            return False

        left_upper_angle = abs(self._line_angle(landmarks[11], landmarks[13]))
        right_upper_angle = abs(self._line_angle(landmarks[12], landmarks[14]))
        left_upper_angle = min(left_upper_angle, 180.0 - left_upper_angle)
        right_upper_angle = min(right_upper_angle, 180.0 - right_upper_angle)

        left_elbow_angle = self._joint_angle(landmarks[11], landmarks[13], landmarks[15])
        right_elbow_angle = self._joint_angle(landmarks[12], landmarks[14], landmarks[16])

        left_upper_arm_is_45 = self._angles_close(left_upper_angle, 45.0)
        right_upper_arm_is_45 = self._angles_close(right_upper_angle, 45.0)
        left_arm_is_straight = self._angles_close(left_elbow_angle, 180.0)
        right_arm_is_straight = self._angles_close(right_elbow_angle, 180.0)

        return (
            left_upper_arm_is_45
            and right_upper_arm_is_45
            and left_arm_is_straight
            and right_arm_is_straight
        )

    def is_sor_pose(self, landmarks: PlayerLandmarks) -> bool:
        required_ids = [11, 12, 13, 14, 15, 16]
        if not self._has_landmarks(landmarks, required_ids):
            return False

        return self._is_sor_direction(
            landmarks=landmarks,
            up_shoulder_id=11,
            up_elbow_id=13,
            up_wrist_id=15,
            down_shoulder_id=12,
            down_elbow_id=14,
            down_wrist_id=16,
        ) or self._is_sor_direction(
            landmarks=landmarks,
            up_shoulder_id=12,
            up_elbow_id=14,
            up_wrist_id=16,
            down_shoulder_id=11,
            down_elbow_id=13,
            down_wrist_id=15,
        )

    def _is_sor_direction(
        self,
        landmarks: PlayerLandmarks,
        up_shoulder_id: int,
        up_elbow_id: int,
        up_wrist_id: int,
        down_shoulder_id: int,
        down_elbow_id: int,
        down_wrist_id: int,
    ) -> bool:
        up_shoulder = landmarks[up_shoulder_id]
        up_elbow = landmarks[up_elbow_id]
        up_wrist = landmarks[up_wrist_id]
        down_shoulder = landmarks[down_shoulder_id]
        down_elbow = landmarks[down_elbow_id]
        down_wrist = landmarks[down_wrist_id]

        up_elbow_angle = self._joint_angle(up_shoulder, up_elbow, up_wrist)
        down_elbow_angle = self._joint_angle(down_shoulder, down_elbow, down_wrist)

        up_arm_is_90 = self._angles_close(up_elbow_angle, 90.0)
        down_arm_is_90 = self._angles_close(down_elbow_angle, 90.0)
        up_wrist_is_above_elbow = up_wrist["y"] <= up_elbow["y"] + self.tolerance.position
        down_wrist_is_below_elbow = down_wrist["y"] >= down_elbow["y"] - self.tolerance.position

        return (
            up_arm_is_90
            and down_arm_is_90
            and up_wrist_is_above_elbow
            and down_wrist_is_below_elbow
        )

    def is_jojo_stand2_pose(self, landmarks: PlayerLandmarks) -> bool:
        required_ids = [11, 12, 13, 14, 15, 16]
        if not self._has_landmarks(landmarks, required_ids):
            return False

        return self._is_jojo_stand2_direction(
            landmarks=landmarks,
            up_shoulder_id=11,
            up_elbow_id=13,
            up_wrist_id=15,
            down_elbow_id=14,
            down_wrist_id=16,
        ) or self._is_jojo_stand2_direction(
            landmarks=landmarks,
            up_shoulder_id=12,
            up_elbow_id=14,
            up_wrist_id=16,
            down_elbow_id=13,
            down_wrist_id=15,
        )

    def _is_jojo_stand2_direction(
        self,
        landmarks: PlayerLandmarks,
        up_shoulder_id: int,
        up_elbow_id: int,
        up_wrist_id: int,
        down_elbow_id: int,
        down_wrist_id: int,
    ) -> bool:
        up_shoulder = landmarks[up_shoulder_id]
        up_elbow = landmarks[up_elbow_id]
        up_wrist = landmarks[up_wrist_id]
        down_elbow = landmarks[down_elbow_id]
        down_wrist = landmarks[down_wrist_id]

        up_elbow_angle = self._joint_angle(up_shoulder, up_elbow, up_wrist)

        up_arm_is_90 = self._angles_close(up_elbow_angle, 90.0)
        up_wrist_is_above_elbow = up_wrist["y"] <= up_elbow["y"] + self.tolerance.position
        down_wrist_is_below_elbow = down_wrist["y"] >= down_elbow["y"] - self.tolerance.position
        elbows_are_same_height = abs(up_elbow["y"] - down_elbow["y"]) <= self.tolerance.position
        up_elbow_is_inside_shoulder = (
            up_elbow["x"] >= up_shoulder["x"] - self.tolerance.position
            if up_shoulder_id == 11
            else up_elbow["x"] <= up_shoulder["x"] + self.tolerance.position
        )

        return (
            up_arm_is_90
            and up_wrist_is_above_elbow
            and down_wrist_is_below_elbow
            and elbows_are_same_height
            and up_elbow_is_inside_shoulder
        )

    def is_no_pose(self, landmarks: PlayerLandmarks) -> bool:
        required_ids = [0, 7, 8, 11, 12, 13, 14, 15, 16]
        if not self._has_landmarks(landmarks, required_ids):
            return False

        return self._is_no_direction(
            landmarks=landmarks,
            up_ear_id=8,
            up_shoulder_id=11,
            up_elbow_id=13,
            up_wrist_id=15,
            down_shoulder_id=12,
            down_elbow_id=14,
            is_left_wrist=True,
        ) or self._is_no_direction(
            landmarks=landmarks,
            up_ear_id=7,
            up_shoulder_id=12,
            up_elbow_id=14,
            up_wrist_id=16,
            down_shoulder_id=11,
            down_elbow_id=13,
            is_left_wrist=False,
        )

    def _is_no_direction(
        self,
        landmarks: PlayerLandmarks,
        up_ear_id: int,
        up_shoulder_id: int,
        up_elbow_id: int,
        up_wrist_id: int,
        down_shoulder_id: int,
        down_elbow_id: int,
        is_left_wrist: bool,
    ) -> bool:
        nose = landmarks[0]
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        up_ear = landmarks[up_ear_id]
        up_shoulder = landmarks[up_shoulder_id]
        up_elbow = landmarks[up_elbow_id]
        up_wrist = landmarks[up_wrist_id]
        down_shoulder = landmarks[down_shoulder_id]
        down_elbow = landmarks[down_elbow_id]
        shoulder_y = (left_shoulder["y"] + right_shoulder["y"]) / 2
        upper_arm_angle = abs(self._line_angle(up_shoulder, up_elbow))
        down_upper_arm_angle = abs(self._line_angle(down_shoulder, down_elbow))

        upper_arm_is_vertical = self._angles_close(upper_arm_angle, 90.0)
        down_upper_arm_is_vertical = self._angles_close(down_upper_arm_angle, 90.0)
        wrist_is_near_shoulder_height = (
            abs(up_wrist["y"] - shoulder_y) <= self.tolerance.position
        )
        wrist_is_outside_nose = (
            up_wrist["x"] >= nose["x"] - self.tolerance.position
            if is_left_wrist
            else up_wrist["x"] <= nose["x"] + self.tolerance.position
        )
        wrist_is_near_ear_x = abs(up_wrist["x"] - up_ear["x"]) <= self.tolerance.position

        return (
            upper_arm_is_vertical
            and down_upper_arm_is_vertical
            and wrist_is_near_shoulder_height
            and wrist_is_outside_nose
            and wrist_is_near_ear_x
        )

    def is_what_pose(self, landmarks: PlayerLandmarks) -> bool:
        required_ids = [11, 12, 13, 14, 15, 16]
        if not self._has_landmarks(landmarks, required_ids):
            return False

        return self._is_what_direction(
            landmarks=landmarks,
            up_shoulder_id=11,
            up_elbow_id=13,
            up_wrist_id=15,
            down_shoulder_id=12,
            down_elbow_id=14,
            down_wrist_id=16,
        ) or self._is_what_direction(
            landmarks=landmarks,
            up_shoulder_id=12,
            up_elbow_id=14,
            up_wrist_id=16,
            down_shoulder_id=11,
            down_elbow_id=13,
            down_wrist_id=15,
        )

    def _is_what_direction(
        self,
        landmarks: PlayerLandmarks,
        up_shoulder_id: int,
        up_elbow_id: int,
        up_wrist_id: int,
        down_shoulder_id: int,
        down_elbow_id: int,
        down_wrist_id: int,
    ) -> bool:
        up_shoulder = landmarks[up_shoulder_id]
        up_elbow = landmarks[up_elbow_id]
        up_wrist = landmarks[up_wrist_id]
        down_shoulder = landmarks[down_shoulder_id]
        down_elbow = landmarks[down_elbow_id]
        down_wrist = landmarks[down_wrist_id]

        up_elbow_angle = self._joint_angle(up_shoulder, up_elbow, up_wrist)
        down_elbow_angle = self._joint_angle(down_shoulder, down_elbow, down_wrist)

        up_shoulder_is_higher = (
            up_shoulder["y"] <= down_shoulder["y"] - self.tolerance.position
        )
        up_arm_is_straight = self._angles_close(up_elbow_angle, 180.0)
        down_arm_is_straight = self._angles_close(down_elbow_angle, 180.0)
        arms_point_right = (
            up_wrist["x"] >= up_elbow["x"] - self.tolerance.position
            and down_wrist["x"] >= down_elbow["x"] - self.tolerance.position
        )
        arms_point_left = (
            up_wrist["x"] <= up_elbow["x"] + self.tolerance.position
            and down_wrist["x"] <= down_elbow["x"] + self.tolerance.position
        )
        lower_wrist_matches_direction = (
            (arms_point_right and down_wrist_id == 15)
            or (arms_point_left and down_wrist_id == 16)
        )

        return (
            up_shoulder_is_higher
            and up_arm_is_straight
            and down_arm_is_straight
            and lower_wrist_matches_direction
        )

    def is_jackson_pose(self, landmarks: PlayerLandmarks) -> bool:
        required_ids = [0, 11, 12, 13, 14, 15, 16]
        if not self._has_landmarks(landmarks, required_ids):
            return False

        return self._is_jackson_direction(
            landmarks=landmarks,
            bent_shoulder_id=11,
            bent_elbow_id=13,
            bent_wrist_id=15,
            straight_shoulder_id=12,
            straight_elbow_id=14,
            straight_wrist_id=16,
        ) or self._is_jackson_direction(
            landmarks=landmarks,
            bent_shoulder_id=12,
            bent_elbow_id=14,
            bent_wrist_id=16,
            straight_shoulder_id=11,
            straight_elbow_id=13,
            straight_wrist_id=15,
        )

    def _is_jackson_direction(
        self,
        landmarks: PlayerLandmarks,
        bent_shoulder_id: int,
        bent_elbow_id: int,
        bent_wrist_id: int,
        straight_shoulder_id: int,
        straight_elbow_id: int,
        straight_wrist_id: int,
    ) -> bool:
        nose = landmarks[0]
        bent_shoulder = landmarks[bent_shoulder_id]
        bent_elbow = landmarks[bent_elbow_id]
        bent_wrist = landmarks[bent_wrist_id]
        straight_shoulder = landmarks[straight_shoulder_id]
        straight_elbow = landmarks[straight_elbow_id]
        straight_wrist = landmarks[straight_wrist_id]

        bent_elbow_angle = self._joint_angle(bent_shoulder, bent_elbow, bent_wrist)
        straight_elbow_angle = self._joint_angle(
            straight_shoulder,
            straight_elbow,
            straight_wrist,
        )

        bent_elbow_is_above_shoulder = (
            bent_elbow["y"] <= bent_shoulder["y"] - self.tolerance.position
        )
        bent_wrist_is_above_nose = bent_wrist["y"] <= nose["y"] + self.tolerance.position
        #bent_arm_is_60 = self._angles_close(bent_elbow_angle, 60.0)
        straight_arm_is_straight = self._angles_close(straight_elbow_angle, 180.0)
        straight_elbow_is_outside_shoulder = (
            straight_elbow["x"] <= straight_shoulder["x"] - self.tolerance.position
            if straight_shoulder_id == 11
            else straight_elbow["x"] >= straight_shoulder["x"] + self.tolerance.position
        )
        self.debug_bool_list([
            bent_elbow_is_above_shoulder,
            bent_wrist_is_above_nose,
            bent_elbow_angle,
            straight_arm_is_straight,
            straight_elbow_is_outside_shoulder])
        return (
            bent_elbow_is_above_shoulder
            and bent_wrist_is_above_nose
            #and bent_arm_is_60
            and straight_arm_is_straight
            and straight_elbow_is_outside_shoulder
        )

    def _is_jojo_stand1_direction(
        self,
        landmarks: PlayerLandmarks,
        up_shoulder_id: int,
        up_elbow_id: int,
        up_wrist_id: int,
        down_shoulder_id: int,
        down_elbow_id: int,
        down_wrist_id: int,
    ) -> bool:
        nose = landmarks[0]
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        shoulder_y = (left_shoulder["y"] + right_shoulder["y"]) / 2

        up_shoulder = landmarks[up_shoulder_id]
        up_elbow = landmarks[up_elbow_id]
        up_wrist = landmarks[up_wrist_id]
        down_shoulder = landmarks[down_shoulder_id]
        down_elbow = landmarks[down_elbow_id]
        down_wrist = landmarks[down_wrist_id]

        up_elbow_angle = self._joint_angle(up_wrist, up_elbow, up_shoulder)
        down_upper_angle = abs(self._line_angle(down_elbow, down_wrist))
        down_upper_angle = min(down_upper_angle, 180.0 - down_upper_angle)

        up_wrist_is_between_nose_and_shoulders = (
            nose["y"] - self.tolerance.position
            <= up_wrist["y"]
            <= shoulder_y + self.tolerance.position
        )
        up_arm_is_bent = self._angles_close(up_elbow_angle, 30.0)
        down_upper_arm_is_60 = self._angles_close(down_upper_angle, 60.0)
        down_wrist_is_below_elbow = (
            down_wrist["y"] >= down_elbow["y"] - self.tolerance.position
        )
        up_elbow_is_inside_shoulder = (
            up_elbow["x"] >= up_shoulder["x"] - self.tolerance.position
            if up_shoulder_id == 11
            else up_elbow["x"] <= up_shoulder["x"] + self.tolerance.position
        )
        
        return (
            up_wrist_is_between_nose_and_shoulders
            and up_arm_is_bent
            and down_upper_arm_is_60
            and down_wrist_is_below_elbow
            and up_elbow_is_inside_shoulder
        )

    def _is_so_cool_direction(
        self,
        landmarks: PlayerLandmarks,
        diagonal_elbow_id: int,
        diagonal_wrist_id: int,
        horizontal_elbow_id: int,
        horizontal_wrist_id: int,
    ) -> bool:
        diagonal_angle = abs(self._line_angle(
            landmarks[diagonal_elbow_id],
            landmarks[diagonal_wrist_id],
        ))
        horizontal_angle = abs(self._line_angle(
            landmarks[horizontal_elbow_id],
            landmarks[horizontal_wrist_id],
        ))

        diagonal_arm_is_45 = (
            self._angles_close(diagonal_angle, 45.0)
            or self._angles_close(diagonal_angle, 135.0)
        )
        horizontal_arm_is_180 = (
            self._angles_close(horizontal_angle, 0.0)
            or self._angles_close(horizontal_angle, 180.0)
        )
        wrists_are_same_height = (
            abs(landmarks[diagonal_wrist_id]["y"] - landmarks[horizontal_wrist_id]["y"])
            <= self.tolerance.position
        )

        return diagonal_arm_is_45 and horizontal_arm_is_180 and wrists_are_same_height

    def _is_happy_direction(
        self,
        landmarks: PlayerLandmarks,
        up_ear_id: int,
        up_shoulder_id: int,
        up_elbow_id: int,
        up_wrist_id: int,
        down_shoulder_id: int,
        down_elbow_id: int,
        down_wrist_id: int,
        down_hip_id: int,
    ) -> bool:
        up_ear = landmarks[up_ear_id]
        up_shoulder = landmarks[up_shoulder_id]
        up_elbow = landmarks[up_elbow_id]
        up_wrist = landmarks[up_wrist_id]
        down_shoulder = landmarks[down_shoulder_id]
        down_elbow = landmarks[down_elbow_id]
        down_wrist = landmarks[down_wrist_id]
        down_hip = landmarks[down_hip_id]

        up_elbow_angle = self._joint_angle(up_shoulder, up_elbow, up_wrist)
        down_elbow_angle = self._joint_angle(down_shoulder, down_elbow, down_wrist)

        up_arm_is_bent = self._angles_close(up_elbow_angle, 45.0)
        up_wrist_is_near_ear = abs(up_wrist["y"] - up_ear["y"]) <= self.tolerance.position
        
        down_wrist_is_between_elbow_and_hip = (
            down_elbow["y"] + self.tolerance.position
            <= down_wrist["y"]
            <= down_hip["y"] + self.tolerance.position
        )

        return (
            up_arm_is_bent
            and up_wrist_is_near_ear
            
            and down_wrist_is_between_elbow_and_hip
        )

    def _is_dab_direction(
        self,
        landmarks: PlayerLandmarks,
        extended_shoulder_id: int,
        extended_wrist_id: int,
        cover_elbow_id: int,
        cover_wrist_id: int,
        direction: int,
    ) -> bool:
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        shoulder_y = (left_shoulder["y"] + right_shoulder["y"]) / 2
        shoulder_min_x = min(left_shoulder["x"], right_shoulder["x"])
        shoulder_max_x = max(left_shoulder["x"], right_shoulder["x"])

        extended_shoulder = landmarks[extended_shoulder_id]
        extended_elbow = landmarks[extended_shoulder_id + 2]
        extended_wrist = landmarks[extended_wrist_id]
        cover_elbow = landmarks[cover_elbow_id]
        cover_wrist = landmarks[cover_wrist_id]

        both_wrists_are_high = (
            extended_wrist["y"] <= shoulder_y + self.tolerance.position
            and cover_wrist["y"] <= shoulder_y + self.tolerance.position
        )
        
        extended_wrist_is_outside_shoulder = (
            extended_wrist["x"] <= shoulder_min_x - self.tolerance.position
            if direction == -1
            else extended_wrist["x"] >= shoulder_max_x + self.tolerance.position
        )

        extended_upper_angle = self._line_angle(extended_shoulder, extended_elbow)
        extended_lower_angle = self._line_angle(extended_elbow, extended_wrist)
        cover_lower_angle = self._line_angle(cover_elbow, cover_wrist)

        extended_arm_is_straight = self._angles_close(extended_upper_angle, extended_lower_angle)
        cover_arm_matches_extended_arm = self._angles_close(
            extended_upper_angle,
            cover_lower_angle,
        )

        return (
            both_wrists_are_high
            and extended_wrist_is_outside_shoulder
            and extended_arm_is_straight
            and cover_arm_matches_extended_arm
        )

    def _angles_close(self, first: float, second: float) -> bool:
        diff = abs((first - second + 180) % 360 - 180)
        return diff <= self.tolerance.angle

    @staticmethod
    def debug_bool_list(values: List[bool]) -> None:
        print(values)

    @staticmethod
    def _joint_angle(
        first: Dict[str, float],
        center: Dict[str, float],
        second: Dict[str, float],
    ) -> float:
        first_angle = math.atan2(first["y"] - center["y"], first["x"] - center["x"])
        second_angle = math.atan2(second["y"] - center["y"], second["x"] - center["x"])
        diff = abs(math.degrees(first_angle - second_angle))
        return min(diff, 360.0 - diff)

    @staticmethod
    def _has_landmarks(landmarks: PlayerLandmarks, required_ids: List[int]) -> bool:
        return all(landmark_id in landmarks for landmark_id in required_ids)

    @staticmethod
    def _head_center(landmarks: PlayerLandmarks) -> Dict[str, float]:
        head_landmarks = [landmarks[0], landmarks[7], landmarks[8]]
        return {
            "x": sum(landmark["x"] for landmark in head_landmarks) / len(head_landmarks),
            "y": sum(landmark["y"] for landmark in head_landmarks) / len(head_landmarks),
        }

    @staticmethod
    def _line_angle(start: Dict[str, float], end: Dict[str, float]) -> float:
        dx = end["x"] - start["x"]
        dy = start["y"] - end["y"]
        return math.degrees(math.atan2(dy, dx))
