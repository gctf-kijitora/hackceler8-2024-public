import game.engine.arcade_system.arcade_system
import kijitora.kstate as kstate
from kijitora.keyhistory import exists_replay, get_autoload_replay_name, load_key_history_from_name
from kijitora.config import arcade_port
from game.engine.keys import Keys
import pickle
import sys


import logging
import os
from pwn import listen

from game import constants
from game.components.items import check_item_loaded
from subprocess import Popen, PIPE


from importlib.machinery import SourceFileLoader
game_module = SourceFileLoader("game", "game/engine/arcade_system/game").load_module()

class HackedArcadeSystem(game.engine.arcade_system.arcade_system.ArcadeSystem):
    def __init__(self, *args, **kwargs):
        self.game_socket = listen(arcade_port)
        super().__init__(*args, **kwargs)

        self.game.key_history.clear()
        
        if not kstate.loading_key_history_from and exists_replay(get_autoload_replay_name("arcade")):
            kstate.loading_key_history_from = get_autoload_replay_name("arcade")

        if kstate.loading_key_history_from:
            key_history, label = load_key_history_from_name(kstate.loading_key_history_from)
            if label == "arcade":
                kstate.replay_start(key_history, instant=kstate.instant_replay)
                kstate.instant_replay = False
                kstate.loading_key_history_from = None            
        else:
            kstate.loaded_key_history = None
        self._recv_game_object()

    def tick(self):
        super().tick()
        if self.proc is None:
            return
        self._recv_game_object()

    def close(self):
        super().close()
        self.game_socket.close()

    def _recv_game_object(self):
        recv_len = int.from_bytes(self.game_socket.recv(4), "little")
        if recv_len == 0:
            kstate.arcade_game = None
            return
        pickled = self.game_socket.recv(recv_len)
        old_main = sys.modules["__main__"]
        sys.modules["__main__"] = game_module
        kstate.arcade_game = pickle.loads(pickled)
        sys.modules["__main__"] = old_main