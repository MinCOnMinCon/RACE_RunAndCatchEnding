from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import cv2
import pygame

from player_state import PlayerStateResult
from pose_library import PoseRule


@dataclass(frozen=True)
class RenderData:
    drawn_frame: object
    cur_speed_by_player: Dict[int, float]
    cur_pos_by_player: Dict[int, float]
    remained_distance_by_player: Dict[int, float]
    success_by_player: Dict[int, bool]
    pose_rules_by_player: Dict[int, PoseRule | None]


class Renderer:
    def __init__(self, window_name: str = "RACE"):
        pygame.init()
        pygame.font.init()
        pygame.mixer.init()

        self.window_name = window_name
        self.player_count = 2

        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption(self.window_name)

        self.window_width, self.window_height = self.screen.get_size()
        self.player_width = self.window_width // self.player_count
        self.target_pose_box_size = min(360, self.player_width - 80, self.window_height // 3)
        self.progress_bar_height = min(760, self.window_height - 260)
        self.panel_alpha = 145
        self.success_flash_duration = 0.35
        self.success_flash_started_at: Dict[int, float] = {
            player_id: -999.0 for player_id in range(self.player_count)
        }
        self.success_sounds = self._load_success_sounds()

        self.font_large = self._make_font(36)
        self.font_medium = self._make_font(28)
        self.font_small = self._make_font(24)

    def render(self, data: RenderData):
        if data.drawn_frame is None:
            return

        self._update_success_feedback(data)
        self._draw_camera_frame(data.drawn_frame)
        self._draw_divider()

        for player_id in range(self.player_count):
            self._draw_player_ui(data, player_id)

        pygame.display.flip()

    def show_loading(self) -> None:
        loading_sound = self._load_sound("loading.mp3")
        if loading_sound is not None:
            loading_sound.play()

        self.screen.fill((0, 0, 0))

        loading_image = self._load_image("loading_img.jpg") or self._load_image("loading_img.png")
        if loading_image is not None:
            image_rect = loading_image.get_rect(center=self.screen.get_rect().center)
            self.screen.blit(loading_image, image_rect)

        loading_font = self._make_font(72)
        text_y = self.window_height // 2 - loading_font.get_height() // 2
        self._draw_centered_text("Loading...", loading_font, self.window_width // 2, text_y)

        pygame.display.flip()

    def show_countdown(self, data: RenderData) -> None:
        for text in ("Ready?", "3", "2", "1", "Go!"):
            self.render(data)
            self._draw_countdown_overlay(text)
            pygame.display.flip()
            pygame.time.wait(700)

    def show_finish(self, winner_id: int, data: RenderData | None = None) -> None:
        self.stop_bgm()
        self._show_finish_text(data)
        self._show_winner_screen(
            image_name=f"player{winner_id + 1}_win.png",
            winner_text=f"PLAYER {winner_id + 1} WIN!!!",
        )

    def play_bgm(self) -> None:
        bgm_path = self._get_sound_path("main_bgm.mp3")
        if bgm_path is None:
            return

        try:
            pygame.mixer.music.load(str(bgm_path))
            pygame.mixer.music.play(-1)
        except pygame.error:
            return

    def stop_bgm(self) -> None:
        pygame.mixer.music.stop()

    def make_render_data(
        self,
        pose_result,
        player_state_results: Dict[int, PlayerStateResult],
    ) -> RenderData:
        return RenderData(
            drawn_frame=pose_result.drawn_frame,
            cur_speed_by_player={
                player_id: state_result.cur_speed
                for player_id, state_result in player_state_results.items()
            },
            cur_pos_by_player={
                player_id: state_result.cur_pos
                for player_id, state_result in player_state_results.items()
            },
            remained_distance_by_player={
                player_id: state_result.remained_distance
                for player_id, state_result in player_state_results.items()
            },
            success_by_player=pose_result.success_by_player,
            pose_rules_by_player=pose_result.pose_rules_by_player,
        )

    def should_quit(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                return True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return True
        return False

    def close(self):
        self.stop_bgm()
        pygame.quit()

    def _draw_camera_frame(self, frame) -> None:
        resized_frame = cv2.resize(frame, (self.window_width, self.window_height))
        rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
        surface = pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))
        self.screen.blit(surface, (0, 0))

    def _draw_divider(self) -> None:
        center_x = self.window_width // 2
        pygame.draw.line(
            self.screen,
            (255, 255, 255),
            (center_x, 0),
            (center_x, self.window_height),
            3,
        )

    def _draw_player_ui(self, data: RenderData, player_id: int) -> None:
        area_x = player_id * self.player_width

        pose_rule = data.pose_rules_by_player.get(player_id)
        pose_name = pose_rule.name if pose_rule else "None"

        self._draw_player_border(data, player_id, area_x)
        self._draw_target_pose(area_x + 16, 16, pose_name)
        self._draw_player_stats(data, player_id, area_x)
        self._draw_progress_track(data, player_id, area_x)

    def _draw_player_border(self, data: RenderData, player_id: int, area_x: int) -> None:
        rect = pygame.Rect(area_x, 0, self.player_width, self.window_height)
        border_color = (255, 255, 255, 80)
        flash_strength = self._get_success_flash_strength(player_id)

        if flash_strength > 0:
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            for width, alpha in ((18, 55), (10, 90), (4, 180)):
                pygame.draw.rect(
                    glow,
                    (80, 255, 120, int(alpha * flash_strength)),
                    glow.get_rect().inflate(-width, -width),
                    width,
                )
            self.screen.blit(glow, rect.topleft)
            border_color = (80, 255, 120, int(230 * flash_strength))

        border = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(border, border_color, border.get_rect(), 2)
        self.screen.blit(border, rect.topleft)

    def _draw_target_pose(self, x: int, y: int, pose_name: str) -> None:
        rect = pygame.Rect(x, y, self.target_pose_box_size, self.target_pose_box_size)
        self._draw_panel(rect, alpha=120)
        pygame.draw.rect(self.screen, (255, 255, 255), rect, 3)

        self._draw_centered_text(
            pose_name,
            self.font_medium,
            rect.centerx,
            rect.centery - self.font_medium.get_height() // 2,
        )

    def _draw_player_stats(self, data: RenderData, player_id: int, area_x: int) -> None:
        speed = data.cur_speed_by_player.get(player_id, 0.0)
        cur_pos = data.cur_pos_by_player.get(player_id, 0.0)
        remained_distance = data.remained_distance_by_player.get(player_id, 0.0)
        total_distance = cur_pos + remained_distance
        speed_text = f"{speed:.1f} m/s"
        distance_text = f"{cur_pos:.1f} m / {total_distance:.1f} m"
        boost_text = "+4 m/s"
        boost_strength = self._get_success_flash_strength(player_id)

        x = area_x + 28
        y = self.window_height - 150
        speed_row_width = (
            self.font_small.size("SPEED")[0]
            + 34
            + self.font_medium.size(speed_text)[0]
            + 18
            + self.font_small.size(boost_text)[0]
        )
        distance_width = self.font_small.size(distance_text)[0]
        panel_width = min(
            max(speed_row_width, distance_width) + 42,
            self.player_width - 150,
        )
        panel_rect = pygame.Rect(x - 12, y - 12, panel_width, 104)

        self._draw_text(f"PLAYER {player_id + 1}", self.font_medium, panel_rect.left, panel_rect.top - 38)
        self._draw_panel(panel_rect)
        self._draw_text("SPEED", self.font_small, x, y, (160, 230, 255))
        self._draw_text(speed_text, self.font_medium, x + 116, y - 4)
        if boost_strength > 0:
            boost_x = x + 116 + self.font_medium.size(speed_text)[0] + 18
            boost_color = (
                int(255 - 175 * boost_strength),
                255,
                int(255 - 135 * boost_strength),
            )
            self._draw_text(boost_text, self.font_small, boost_x, y + 2, boost_color)
        self._draw_text(distance_text, self.font_small, x, y + 48)

    def _draw_progress_track(self, data: RenderData, player_id: int, area_x: int) -> None:
        cur_pos = data.cur_pos_by_player.get(player_id, 0.0)
        remained_distance = data.remained_distance_by_player.get(player_id, 0.0)
        total_distance = max(1.0, cur_pos + remained_distance)
        progress = max(0.0, min(1.0, cur_pos / total_distance))

        panel_width = 118
        panel_height = min(self.progress_bar_height + 110, self.window_height - 140)
        panel_x = area_x + self.player_width - panel_width - 24
        panel_y = (self.window_height - panel_height) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        self._draw_panel(panel_rect)

        line_x = panel_rect.centerx
        line_top = panel_rect.top + 66
        line_bottom = panel_rect.bottom - 66
        marker_y = int(line_bottom - (line_bottom - line_top) * progress)

        self._draw_centered_text("FINISH", self.font_small, line_x, panel_rect.top + 22)
        pygame.draw.line(self.screen, (230, 230, 230), (line_x, line_top), (line_x, line_bottom), 4)
        pygame.draw.line(self.screen, (230, 230, 230), (line_x - 18, line_top), (line_x + 18, line_top), 3)
        pygame.draw.line(
            self.screen,
            (230, 230, 230),
            (line_x - 18, line_bottom),
            (line_x + 18, line_bottom),
            3,
        )
        pygame.draw.circle(self.screen, (80, 255, 120), (line_x, marker_y), 13)
        pygame.draw.circle(self.screen, (255, 255, 255), (line_x, marker_y), 13, 2)
        self._draw_centered_text("START", self.font_small, line_x, panel_rect.bottom - 42)

    def _update_success_feedback(self, data: RenderData) -> None:
        for player_id, is_success in data.success_by_player.items():
            if not is_success:
                continue

            self.success_flash_started_at[player_id] = time.monotonic()
            success_sound = self.success_sounds.get(player_id)
            if success_sound is not None:
                success_sound.play()

    def _get_success_flash_strength(self, player_id: int) -> float:
        elapsed = time.monotonic() - self.success_flash_started_at.get(player_id, -999.0)
        if elapsed >= self.success_flash_duration:
            return 0.0

        return 1.0 - elapsed / self.success_flash_duration

    def _draw_panel(self, rect: pygame.Rect, alpha: int | None = None) -> None:
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel.fill((0, 0, 0, alpha if alpha is not None else self.panel_alpha))
        pygame.draw.rect(panel, (255, 255, 255, 70), panel.get_rect(), 2)
        self.screen.blit(panel, rect.topleft)

    def _draw_text(
        self,
        text: str,
        font,
        x: int,
        y: int,
        color: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        shadow = font.render(text, True, (0, 0, 0))
        surface = font.render(text, True, color)
        self.screen.blit(shadow, (x + 2, y + 2))
        self.screen.blit(surface, (x, y))

    def _draw_centered_text(
        self,
        text: str,
        font,
        center_x: int,
        y: int,
        color: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        surface = font.render(text, True, color)
        shadow = font.render(text, True, (0, 0, 0))
        x = center_x - surface.get_width() // 2
        self.screen.blit(shadow, (x + 2, y + 2))
        self.screen.blit(surface, (x, y))

    def _draw_countdown_overlay(self, text: str) -> None:
        overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 80))
        self.screen.blit(overlay, (0, 0))

        font = self._make_font(120 if text != "Ready?" else 88)
        text_y = self.window_height // 2 - font.get_height() // 2
        self._draw_centered_text(text, font, self.window_width // 2, text_y)

    @staticmethod
    def _make_font(size: int):
        return pygame.font.SysFont("malgungothic", size) or pygame.font.Font(None, size)

    def _show_finish_text(self, data: RenderData | None = None) -> None:
        finish_sound = self._load_sound("finish.mp3")
        if finish_sound is not None:
            finish_sound.play()

        if data is not None:
            self.render(data)
        else:
            self.screen.fill((0, 0, 0))

        overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 80))
        self.screen.blit(overlay, (0, 0))

        font = self._make_font(110)
        text_y = self.window_height // 2 - font.get_height() // 2
        self._draw_centered_text("Finish!", font, self.window_width // 2, text_y)
        pygame.display.flip()
        pygame.time.wait(3000)

    def _show_winner_screen(self, image_name: str, winner_text: str) -> None:
        victory_sound = self._load_sound("victory.mp3")
        if victory_sound is not None:
            victory_sound.play()

        self.screen.fill((0, 0, 0))

        winner_image = self._load_image(image_name)
        if winner_image is not None:
            image_rect = winner_image.get_rect(center=self.screen.get_rect().center)
            self.screen.blit(winner_image, image_rect)

        font = self._make_font(92)
        text_y = self.window_height // 2 - font.get_height() // 2
        self._draw_centered_text(winner_text, font, self.window_width // 2, text_y)
        pygame.display.flip()
        pygame.time.wait(3000)

    def _load_image(self, image_name: str):
        image_path = Path(__file__).with_name("image") / image_name
        if not image_path.exists():
            return None

        try:
            image = pygame.image.load(str(image_path)).convert()
        except pygame.error:
            return None

        image_width, image_height = image.get_size()
        scale = min(self.window_width / image_width, self.window_height / image_height)
        scaled_size = (
            max(1, int(image_width * scale)),
            max(1, int(image_height * scale)),
        )
        return pygame.transform.smoothscale(image, scaled_size)

    def _load_success_sounds(self) -> Dict[int, pygame.mixer.Sound]:
        sounds = {}

        for player_id in range(self.player_count):
            sound = self._load_sound(f"correct_player{player_id + 1}.mp3")
            if sound is not None:
                sounds[player_id] = sound

        return sounds

    def _load_sound(self, sound_name: str):
        sound_path = self._get_sound_path(sound_name)
        if sound_path is None:
            return None

        try:
            return pygame.mixer.Sound(str(sound_path))
        except pygame.error:
            return None

    @staticmethod
    def _get_sound_path(sound_name: str):
        sound_path = Path(__file__).with_name("sound") / sound_name
        return sound_path if sound_path.exists() else None
