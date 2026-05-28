from __future__ import annotations

from datetime import datetime

from pose_connector import PoseConnector
from renderer import RenderData, Renderer


class GameManager:
    def __init__(self):
        self.pose_connector = PoseConnector()
        self.renderer = Renderer()

    def run(self):
        try:
            while True:
                pose_result = self.pose_connector.update()
                render_data = self._make_render_data(pose_result)

                self.renderer.render(render_data)
                self._print_success_players(pose_result.success_by_player)

                if self.renderer.should_quit():
                    break
        finally:
            self.close()

    def close(self):
        self.pose_connector.close()
        self.renderer.close()

    def _make_render_data(self, pose_result) -> RenderData:
        return RenderData(
            drawn_frame=pose_result.drawn_frame,
            pose_rules_by_player=pose_result.pose_rules_by_player,
        )

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
