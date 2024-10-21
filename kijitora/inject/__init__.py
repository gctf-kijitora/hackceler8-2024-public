import logging
import moderngl_window as mglw
from collections import deque
from copy import deepcopy
import numpy as np
from game.engine.keys import Keys
import game
import kijitora.kstate as kstate


def inject_class(cls, hacked_cls):
    for subclass in cls.__subclasses__():
        if subclass is not hacked_cls:
            subclass.__bases__ = (hacked_cls,)


import imgui
og_input_text = imgui.input_text
"""
def hacked_input_text(label, value):
    def callback(data):
        if kstate.paste_text is not None:
            data.insert_chars(data.cursor_pos, kstate.paste_text)
            kstate.paste_text = None
    return og_input_text(label, value, flags=256, callback=callback)
"""
def hacked_input_text(label, value):
    def callback(data):
        if kstate.interactive_sock and kstate.interactive_received == False:
            try:
                l = kstate.interactive_sock.recvline(keepends=False)
            except EOFError:
                print("[+] Connection closed (during freetext)")
                kstate.interactive_sock = None
                kstate.interactive_received = True
            else:
                data.insert_chars(data.cursor_pos, "".join(map(chr, l))) # bytes to str
                kstate.interactive_received = True
                kstate.interactive_key_next = Keys.ENTER
    return og_input_text(label, value, flags=256, callback=callback)
imgui.input_text = hacked_input_text

from .textbox import HackedTextbox
inject_class(game.components.textbox.Textbox, HackedTextbox)
game.components.textbox.Textbox = HackedTextbox


from .arcade_system import HackedArcadeSystem
inject_class(game.engine.arcade_system.arcade_system.ArcadeSystem, HackedArcadeSystem)
game.engine.arcade_system.arcade_system.ArcadeSystem = HackedArcadeSystem


from .venator import HackedVenator
inject_class(game.venator.Venator, HackedVenator)
game.venator.Venator = HackedVenator


from .camera import HackedCamera
inject_class(game.engine.gfx.Camera, HackedCamera)
game.engine.gfx.Camera = HackedCamera


from .flags import HackedFlags
inject_class(game.components.flags.Flags, HackedFlags)
game.components.flags.Flags = HackedFlags


from .player import HackedPlayer
inject_class(game.components.player.Player, HackedPlayer)
game.components.player.Player = HackedPlayer
