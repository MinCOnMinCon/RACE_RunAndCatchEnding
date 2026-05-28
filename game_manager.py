from __future__ import annotations

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
                print(pose_result.success_by_player)

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


if __name__ == "__main__":
    GameManager().run()
