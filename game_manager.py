from __future__ import annotations

from datetime import datetime

import pygame

from player_state import PlayerState
from pose_connector import PoseConnector
from renderer import Renderer
from start_screen import StartScreen


class GameManager:
    def __init__(self):
        self.pose_connector = None
        self.renderer = None
        self.player_states = {}

    def launch(self):
        while True:
            selected = StartScreen().run()
            if selected == "start":
                self.start()
                continue

            self.close(quit_pygame=True)
            break

    def start(self):
        self.renderer = Renderer()
        self.renderer.show_loading()
        self._setup_game()
        render_data = self.prepare_game()
        self.renderer.show_countdown(render_data)
        self._reset_player_timers()
        self.renderer.play_bgm()
        self.run()

    def prepare_game(self):
        pose_result = self.pose_connector.prepare_game()
        player_state_results = {
            player_id: player_state.prepare_game()
            for player_id, player_state in self.player_states.items()
        }
        render_data = self.renderer.make_render_data(
            pose_result,
            player_state_results,
        )

        self.renderer.render(render_data)
        return render_data

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

                winner_id = self._get_winner_id(player_state_results)
                if winner_id is not None:
                    self.finish(winner_id, render_data)
                    break

                if self.renderer.should_quit():
                    break
        finally:
            self.close(quit_pygame=False)

    def finish(self, winner_id: int, render_data):
        self.renderer.show_finish(winner_id, render_data)

    def close(self, quit_pygame: bool = True):
        if self.pose_connector is not None:
            self.pose_connector.close()
            self.pose_connector = None
        if self.renderer is not None:
            if quit_pygame:
                self.renderer.close()
            else:
                self.renderer.stop_bgm()
            self.renderer = None
        elif quit_pygame:
            pygame.quit()
        self.player_states = {}

    def _reset_player_timers(self):
        for player_state in self.player_states.values():
            player_state.reset_timer()

    def _setup_game(self):
        self.pose_connector = PoseConnector()
        self.player_states = {
            player_id: PlayerState()
            for player_id in range(self.pose_connector.detector.config.max_players)
        }

    def _get_winner_id(self, player_state_results):
        for player_id, state_result in player_state_results.items():
            if state_result.is_finished:
                return player_id

        return None

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
    GameManager().launch()
