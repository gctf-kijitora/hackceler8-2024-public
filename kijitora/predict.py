import time
from copy import deepcopy
from collections import deque

from game.components.player import Player
from game.engine.keys import Keys
from game.engine.point import Point
from game.venator import Venator

from kijitora.inject.venator import VenatorState
from kijitora.keyhistory import KeyHistory


class Predictor:
    player_skip_attr = ['game', 'weapons']
    def __init__(self):
        self.game: Venator | None = None
        self.orig_player: Player | None = None
        self.raw_pressed_keys = set()
        self.newly_pressed_keys = set()

    def init_state(self, original: Venator) -> bool:
        backup = original.backup()
        if backup is None:
            return False
        self.game = backup.restore(original)

        self.orig_player = Player(Point(original.player.x, original.player.y))
        for key in original.player.__dict__.keys():
            if key in Predictor.player_skip_attr:
                continue

            self.orig_player.__dict__[key] = deepcopy(original.player.__dict__[key])

        self.reset_state()
        return True

    def reset_state(self):
        if self.orig_player is None:
            return

        for key in self.orig_player.__dict__.keys():
            self.game.player.__dict__[key] = deepcopy(self.orig_player.__dict__[key])

        self.raw_pressed_keys.clear()
        self.newly_pressed_keys.clear()
        self.game.player.game = self.game


    def key_press(self, key: Keys) -> None:
        self.raw_pressed_keys.add(key)
        self.newly_pressed_keys.add(key)

    def key_release(self, key: Keys) -> None:
        if key in self.raw_pressed_keys:
            self.raw_pressed_keys.remove(key)

        if key in self.newly_pressed_keys:
            self.newly_pressed_keys.remove(key)

    def leap(self, ntick) -> None:
        history = []
        for _ in range(ntick):
            pos = self.tick()
            history.append(pos)
        return history

    def leap_grounded(self, max_tick: int = 60) -> None:
        history = []
        key_history = KeyHistory(deque())
        for _ in range(max_tick):
            pos, keys = self.tick()
            history.append(pos)
            key_history.append(keys)

            if not self.game.player.in_the_air:
                break

        return history, key_history

    def tick(self) -> None:
        self.game.player.update_movement(self.raw_pressed_keys, self.newly_pressed_keys)
        self.game.physics_engine.tick()
        self.newly_pressed_keys.clear()
        return (self.game.player.x, self.game.player.y), self.raw_pressed_keys
