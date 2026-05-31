from __future__ import annotations

import pygame

from resource_path import ResourcePath


class StartScreen:
    def __init__(self, window_name: str = "RACE"):
        pygame.init()
        pygame.font.init()
        pygame.mixer.init()

        self.window_name = window_name
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption(self.window_name)
        self.window_width, self.window_height = self.screen.get_size()

        self.title_font = self._make_font(72)
        self.button_font = self._make_font(42)
        self.background = self._load_image("start_img.png")
        self.clock = pygame.time.Clock()
        self._play_bgm()

        button_width = 260
        button_height = 82
        button_gap = 34
        center_x = self.window_width // 2
        button_y = int(self.window_height * 0.68)
        self.start_button_rect = pygame.Rect(
            center_x - button_width - button_gap // 2,
            button_y,
            button_width,
            button_height,
        )
        self.exit_button_rect = pygame.Rect(
            center_x + button_gap // 2,
            button_y,
            button_width,
            button_height,
        )

    def run(self) -> str:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._stop_bgm()
                    return "exit"
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                    self._stop_bgm()
                    return "exit"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.start_button_rect.collidepoint(event.pos):
                        self._stop_bgm()
                        return "start"
                    if self.exit_button_rect.collidepoint(event.pos):
                        self._stop_bgm()
                        return "exit"

            mouse_pos = pygame.mouse.get_pos()
            self._draw(mouse_pos)
            pygame.display.flip()
            self.clock.tick(60)

    def _draw(self, mouse_pos: tuple[int, int]) -> None:
        self.screen.fill((0, 0, 0))

        if self.background is not None:
            background_rect = self.background.get_rect(center=self.screen.get_rect().center)
            self.screen.blit(self.background, background_rect)

        overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 70))
        self.screen.blit(overlay, (0, 0))

        title_y = int(self.window_height * 0.34)
        self._draw_centered_text(
            "RACE : Run And Catch Ending",
            self.title_font,
            self.window_width // 2,
            title_y,
        )
        self._draw_button(self.start_button_rect, "Start", mouse_pos)
        self._draw_button(self.exit_button_rect, "Exit", mouse_pos)

    def _draw_button(self, rect: pygame.Rect, text: str, mouse_pos: tuple[int, int]) -> None:
        is_hovered = rect.collidepoint(mouse_pos)
        fill_color = (255, 255, 255, 235) if is_hovered else (20, 20, 20, 185)
        text_color = (0, 0, 0) if is_hovered else (255, 255, 255)
        border_color = (255, 255, 255)

        button = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(button, fill_color, button.get_rect(), border_radius=8)
        pygame.draw.rect(button, border_color, button.get_rect(), 3, border_radius=8)
        self.screen.blit(button, rect.topleft)

        text_surface = self.button_font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=rect.center)
        self.screen.blit(text_surface, text_rect)

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
        self.screen.blit(shadow, (x + 3, y + 3))
        self.screen.blit(surface, (x, y))

    def _load_image(self, image_name: str):
        image_path = ResourcePath.get(f"image/{image_name}")
        if not image_path.exists():
            return None

        try:
            image = pygame.image.load(str(image_path)).convert()
        except pygame.error:
            return None

        image_width, image_height = image.get_size()
        scale = max(self.window_width / image_width, self.window_height / image_height)
        scaled_size = (
            max(1, int(image_width * scale)),
            max(1, int(image_height * scale)),
        )
        return pygame.transform.smoothscale(image, scaled_size)

    def _play_bgm(self) -> None:
        bgm_path = self._get_sound_path("start_screen_bgm.mp3")
        if bgm_path is None:
            return

        try:
            pygame.mixer.music.load(str(bgm_path))
            pygame.mixer.music.play(-1)
        except pygame.error:
            return

    @staticmethod
    def _stop_bgm() -> None:
        pygame.mixer.music.stop()

    @staticmethod
    def _get_sound_path(sound_name: str):
        sound_path = ResourcePath.get(f"sound/{sound_name}")
        return sound_path if sound_path.exists() else None

    @staticmethod
    def _make_font(size: int):
        return pygame.font.SysFont("malgungothic", size) or pygame.font.Font(None, size)
