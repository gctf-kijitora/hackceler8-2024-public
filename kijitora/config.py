import json
from typing import Dict
from game.engine.keys import Keys
import os

from kijitora.keys import get_keycode

DATA_DIR = os.path.abspath(os.path.join(__file__, "..", "..", "data"))
KEY_REMAP_CONFIG_DIR = os.path.join(DATA_DIR, "keyremaps")

tick_rate_table = [1, 5, 15, 30, 40, 60, 90, 120, 180, 300]

key_config = {
    "dec_tick_rate": Keys.Z,
    "inc_tick_rate": Keys.X,
    "stop_key_replay": Keys.M,
    "toggle_stop_tick": Keys.C,
    "advance_tick": Keys.V,
    "camera_reset": Keys.U,
    "camera_zoom_in": Keys.I,
    "camera_zoom_out": Keys.O,
    "toggle_invincible": Keys.K,
    "toggle_auto_paint": Keys.Y,
    "tick_undo": Keys.H,
    "tick_redo": Keys.J,
    "toggle_deep_reset": Keys.L,
    "predict_move": Keys.F,
    "key_lock": Keys.T,
    "jump_traj": Keys.G,
    "boss_auto_aim": Keys.B,
    "double_jump": Keys.N,
    "reserved_comma": 44, # get_keycode("COMMA")
    "reserved_period": 46, # get_keycode("PERIOD")
}

# ref: https://github.com/moderngl/moderngl-window/blob/2cf5d630c5326cc5c435d6b01e9292dcc1d1b721/moderngl_window/context/pyglet/keys.py
savestate_slots = [
    "NUMBER_1",
    "NUMBER_2",
    "NUMBER_3",
    "NUMBER_4",
    "NUMBER_5",
]
replay_slots = [
    "NUMBER_6",
    "NUMBER_7",
    "NUMBER_8",
    "NUMBER_9",
    "NUMBER_0",
]

_key_remap = {}
_key_remap_name = "default"

packet_send_delay = 180
max_venator_history = 100

# "Minion hat" のような感じ
extra_items = []

interactive_port = 9999 # Port number for interactive textbox
arcade_port = 9998 # Port number for arcade

def get_key_remap() -> Dict[int, int]:
   return _key_remap
def get_key_remap_name():
   return _key_remap_name

def set_key_remap(remap: Dict[str, str]):
    global _key_remap
    _key_remap = {}
    for from_key_name, to_key_name in remap.items():
        from_key_val, to_key_val = get_keycode(from_key_name), get_keycode(to_key_name)
        if from_key_val is None or to_key_val is None: continue
        _key_remap[from_key_val] = to_key_val
def set_key_remap_name(remap_name: str):
    global _key_remap_name
    _key_remap_name = remap_name

def set_key_remap_by_name(remap_name: str):
    config_path = os.path.join(KEY_REMAP_CONFIG_DIR, remap_name)
    if not os.path.exists(config_path):
        return None

    with open(config_path, 'r') as f:
        remap = json.loads("\n".join([l.split("//")[0] for l in f.readlines()]))
    set_key_remap(remap)
    set_key_remap_name(remap_name)
    open(os.path.join(KEY_REMAP_CONFIG_DIR, "../.default_remap"), "w").write(remap_name)

def setup_key_remap():
    set_key_remap_by_name(open(os.path.join(KEY_REMAP_CONFIG_DIR, "../.default_remap"), "r").read())
