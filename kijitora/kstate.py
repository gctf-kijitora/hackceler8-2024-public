from collections import deque
from typing import List, Tuple
from game.engine.keys import Keys

gui = None

camera_offset_x = 0
camera_offset_y = 0
camera_zoom = 0

# KeysにないKeyがkey codeとして格納される
extra_real_pressed_key = set()
extra_prev_pressed_key = set()

prev_pressed_keys = set()

ticking_stop = False
tick_advance = False
tick_advance_cooltime = 0

key_history_slots = {}

loaded_key_history: List[Tuple[str, int]] | None = None
loading_key_history_from: str | None = None

auto_painting = False
auto_painting_base_pos = None
painting_target_image = None
replay_cur = 0
replay_total = 0
reset_delay = False
teleport_pos = None
path_finding_dest_pos = None
restoring_game = None
fps_history = deque()
ctrl_pressed = False
alt_pressed = False
game_backups = {}
paste_text = None
venator_history = []
venator_history_cursor = 0
invincible = False
path_finding_info_min_dists = None
should_deep_reset = False
last_sent_tick = 0
deepcopy_maps_dict = None
last_predict_hash = None
jump_traj_config = "Stop"
predict_key_history = []
locked_key = set()  # 押しっぱなしになるキー
boss_starting_seed = -1
cheat_stars = 0
interactive_sock = None
interactive_received = False # 受信が完了したか
interactive_key_next = None  # 次に押すべきキー
interactive_key_last_tic = 0 # 最後にキーを押したtick
interactive_selected = False # 選択肢の決定が完了したか
arcade_game = None
instant_replay = False
next_tick_tasks = []
backup_rate = 10
go_boss = False
boss_auto_aim = False

def replay_start(key_history, overwrite=True, instant=False):
    global loaded_key_history, replay_total, replay_cur
    if instant:
        def instant_replay(game):
            global ticking_stop
            while game.screen_fader is not None:
                game.tick()
            game.tick_with_key_history(key_history)
            ticking_stop = True
            print(ticking_stop)
        next_tick_tasks.append(instant_replay)
        return
    if not overwrite and loaded_key_history is not None:
        loaded_key_history = loaded_key_history.merged(key_history)
    elif key_history is None or key_history.length == 0:
        loaded_key_history = None
    else:
        loaded_key_history = key_history
    replay_cur = 0
    if loaded_key_history is None:
        replay_total = 0
    else:
        replay_total = loaded_key_history.length
