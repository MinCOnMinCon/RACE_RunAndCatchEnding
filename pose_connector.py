from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from pose_detector import PlayerLandmarks, PoseDetector
from pose_library import PoseLibrary, PoseRule


@dataclass(frozen=True)
class PoseConnectorResult:
    success_by_player: Dict[int, bool]
    drawn_frame: object
    pose_rules_by_player: Dict[int, PoseRule | None]


class PoseConnector:
    def __init__(
        self,
        detector: PoseDetector | None = None,
        library: PoseLibrary | None = None,
    ):
        self.detector = detector or PoseDetector()
        self.library = library or PoseLibrary()
        self.current_rules_by_player: Dict[int, PoseRule | None] = {
            player_id: None for player_id in range(self.detector.config.max_players)
        }
        self.drawn_frame = None
        self.landmarks_by_player: Dict[int, PlayerLandmarks] = {}
        self.success_by_player: Dict[int, bool] = {
            player_id: True for player_id in range(self.detector.config.max_players)
        }
        self.previous_success_by_player: Dict[int, bool] = {
            player_id: False for player_id in range(self.detector.config.max_players)
        }

    def update(self) -> PoseConnectorResult:
        self._refresh_rules_for_successful_players()

        self.drawn_frame, self.landmarks_by_player = self.detector.process_frame()
        raw_success_by_player = self._check_players()
        self.success_by_player = self._filter_consecutive_success(raw_success_by_player)

        return PoseConnectorResult(
            success_by_player=self.success_by_player,
            drawn_frame=self.drawn_frame,
            pose_rules_by_player=self.current_rules_by_player,
        )

    def get_current_rules(self) -> Dict[int, PoseRule | None]:
        return self.current_rules_by_player

    def get_drawn_frame(self):
        return self.drawn_frame

    def close(self):
        self.detector.close()

    def _check_players(self) -> Dict[int, bool]:
        success_by_player: Dict[int, bool] = {}

        for player_id in range(self.detector.config.max_players):
            pose_rule = self.current_rules_by_player[player_id]
            landmarks = self.landmarks_by_player.get(player_id)
            success_by_player[player_id] = pose_rule.check(landmarks) if pose_rule else False

        return success_by_player

    def _filter_consecutive_success(
        self,
        raw_success_by_player: Dict[int, bool],
    ) -> Dict[int, bool]:
        filtered_success_by_player: Dict[int, bool] = {}

        for player_id, is_success in raw_success_by_player.items():
            filtered_success_by_player[player_id] = (
                is_success
                and not self.previous_success_by_player.get(player_id, False)
            )

        self.previous_success_by_player = dict(filtered_success_by_player)
        return filtered_success_by_player

    def _refresh_rules_for_successful_players(self, rule_id: int | None = None):
        for player_id in range(self.detector.config.max_players):
            if self.success_by_player[player_id]:
                self.current_rules_by_player[player_id] = self.library.get_random_rule(
                    rule_id=rule_id
                )
                self.success_by_player[player_id] = False
