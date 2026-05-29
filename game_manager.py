from __future__ import annotations

from datetime import datetime

from player_state import PlayerState
from pose_connector import PoseConnector
from renderer import Renderer


class GameManager:
    def __init__(self):
        self.pose_connector = PoseConnector()
        self.renderer = Renderer()
        self.player_states = {
            player_id: PlayerState()
            for player_id in range(self.pose_connector.detector.config.max_players)
        }

    def run(self):
        try:
            while True:
                pose_result = self.pose_connector.update()
                player_state_results = {
                    player_id: player_state.update(
                        pose_result.success_by_player.get(player_id, False)
                    )
                    for player_id, player_state in self.player_states.items()
                }
                render_data = self.renderer.make_render_data(
                    pose_result,
                    player_state_results,
                )

                self.renderer.render(render_data)
                self._print_success_players(pose_result.success_by_player)

                if self.renderer.should_quit():
                    break
        finally:
            self.close()

    def close(self):
        self.pose_connector.close()
        self.renderer.close()

    def _print_success_players(self, success_by_player):
        success_players = [
            player_id for player_id, is_success in success_by_player.items() if is_success
        ]

        if not success_players:
            return

        current_time = datetime.now().strftime("%H:%M:%S")
        player_names = ", ".join(f"Player {player_id + 1}" for player_id in success_players)
        print(f"[{current_time}] Success: {player_names}")


if __name__ == "__main__":
    GameManager().run()
