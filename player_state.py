from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlayerStateResult:
    cur_speed: float
    cur_pos: float
    remained_distance: float
    is_finished: bool


@dataclass
class PlayerState:
    total_distance: float = 1612.0
    min_speed: float = 5.5
    max_speed: float = 30.0
    accel_value_per_suc: float = 4.0
    decel_value_per_sec: float = 2.0
    no_decel_duration: float = 3.3
    cur_speed: float = 5.5
    cur_pos: float = 0.0
    remained_distance: float = 1612.0
    no_decel_time: float = 0.0
    dt: float = 0.0
    last_update_time: float = field(default_factory=time.monotonic)

    def update_dt(self) -> None:
        current_time = time.monotonic()
        self.dt = current_time - self.last_update_time
        self.last_update_time = current_time

    def update_speed(self, is_success: bool) -> None:
        if is_success:
            self.cur_speed += self.accel_value_per_suc
            self.no_decel_time = self.no_decel_duration
        elif self.no_decel_time > 0:
            self.no_decel_time = max(0.0, self.no_decel_time - self.dt)
        else:
            self.cur_speed -= self.decel_value_per_sec * self.dt

        self.cur_speed = min(self.max_speed, max(self.min_speed, self.cur_speed))

    def update_distance(self) -> None:
        self.cur_pos += self.cur_speed * self.dt
        self.cur_pos = min(self.total_distance, self.cur_pos)
        self.remained_distance = max(0.0, self.total_distance - self.cur_pos)

    def update(self, is_success: bool) -> PlayerStateResult:
        self.update_dt()
        self.update_speed(is_success)
        self.update_distance()
        return PlayerStateResult(
            cur_speed=self.cur_speed,
            cur_pos=self.cur_pos,
            remained_distance=self.remained_distance,
            is_finished=self.is_finished(),
        )

    def prepare_game(self) -> PlayerStateResult:
        self.dt = 0.0
        return PlayerStateResult(
            cur_speed=self.cur_speed,
            cur_pos=self.cur_pos,
            remained_distance=self.remained_distance,
            is_finished=self.is_finished(),
        )

    def reset_timer(self) -> None:
        self.dt = 0.0
        self.last_update_time = time.monotonic()

    def is_finished(self) -> bool:
        return self.cur_pos >= self.total_distance
