import json
import logging
import pickle
import io
from threading import Thread
import time
import types
from copy import deepcopy
from collections import deque

from game.engine.save_file import apply_save_state
import game.venator
from game.engine.keys import Keys
from game.components.weapon.weapon import Weapon
from game.components.weapon.cannon import Cannon
from game.components.weapon.gun import Gun
from game.components.enemy.enemy import Enemy
from game.components.boss.dialogue_boss import DialogueBoss
from game.components.boss.fighting_boss import FightingBoss
from game.components.items import Item, display_to_name
from game.engine.generics import GenericObject
from game.components.wall import Wall
from game.engine.point import Point
from game.engine.hitbox import Hitbox

from game.network import NetworkConnection
from game.engine.gfx import ShapeLayer, SpriteLayer, CombinedLayer, TextureReference, GuiImage
from game.map.tileset import Tileset

from kijitora.keyhistory import KeyHistory, exists_replay, get_autoload_replay_name, load_key_history_from_name
import kijitora.kstate as kstate
import kijitora.gameutils as gameutils
from kijitora.config import key_config, packet_send_delay, max_venator_history, extra_items

class HackedVenator(game.venator.Venator):
    def __init__(self, *args, **kwargs):
        self.is_main_venator = True
        self.key_history = KeyHistory(deque())
        self.packets = deque()
        self.real_pressed_keys = set()
        self.pkgs_from_server = []
        super().__init__(*args, **kwargs)
        for item_name in extra_items:
            if not any(i.name == display_to_name(item_name) for i in self.items):
                self.items.append(Item(None, display_to_name(item_name), item_name))
        self._check_all_objects()

    def _check_all_objects(self):
        for map_name, tile_map in self.maps_dict.items():
            logging.info(f"checking map: {map_name}")
            for o in tile_map.tiled_map.objects:
                if o.x % 1 != 0 or o.y % 1 != 0:
                    logging.warning(f"non integer coords alert!!! {map_name}: {o.name} ({o.x},{o.y}){" / blocking!" if o.blocking else ""}")

    def tick(self):
        if self.is_main_venator:
            if kstate.ticking_stop and not kstate.tick_advance:
                return
            kstate.tick_advance = False
            if self.ready and not self.module_reloading and not self.waiting_for_server_txt:
                self.raw_pressed_keys = self._pressed_key_hook(self.real_pressed_keys.copy())
        else:
            self.raw_pressed_keys = self.real_pressed_keys.copy()
        self._update_key_history()
        super().tick()

    def send_game_info(self):
        if not self.is_main_venator:
            return
        if self.is_server or self.net is None:
            return
        logging.debug(f"{self.tics} : {self.raw_pressed_keys}")
        msg = {
            "tics": self.tics,
            "state": self.state_hash,
            "keys": [i.serialized for i in self.raw_pressed_keys],
            "text_input": self.get_text_input(),
        }
        force_send = self.waiting_for_server_txt or self.module_reloading or isinstance(self.boss, DialogueBoss) or self.won
        self.packets.append(msg)
        while len(self.packets) > 0:
            msg = self.packets[0]
            if msg["tics"] <= kstate.last_sent_tick:
                self.packets.popleft()
            elif msg["tics"] <= self.tics - packet_send_delay or force_send:
                self.packets.popleft()
                kstate.last_sent_tick = msg["tics"]
                self.net.send_one(json.dumps(msg).encode())
            else:
                break

    def setup_client(self):
        def _process_server_pkgs():
            while True:
                msg = self.net.recv_one()
                game = kstate.gui.game
                if game is None:
                    game = self
                if b"save_state" in msg:
                    logging.info(msg)
                    try:
                        _save_state = json.loads(msg.decode())["save_state"]
                    except Exception as e:
                        logging.critical(
                            f"Failed to parse save state from server: {e}")
                        continue
                    apply_save_state(_save_state, game)
                    logging.info("Loaded save state from server")
                    with game.mutex:
                        game.ready = True
                with game.mutex:
                    game.pkgs_from_server.append(msg)

        Thread(target=_process_server_pkgs, daemon=True).start()

    def recv_from_server(self):
        with self.mutex:
            game = kstate.gui.game
            for msg in reversed(game.pkgs_from_server):
                try:
                    msg = json.loads(msg.decode())
                except Exception as e:
                    logging.critical(f"Failed to decode message: {e}")
                    raise
                if "chat_text" in msg:
                    if game.textbox is not None and game.textbox.from_server:
                        text = msg["chat_text"]
                        logging.info(f"Got chat message from server: \"{text}\"")
                        choices = msg["chat_choices"]
                        if choices is None:
                            choices = []
                        free_text = msg["chat_free_text"]
                        game.textbox.set_text_from_server(text, choices, free_text)
                        game.waiting_for_server_txt = False
                if "u_cheat" in msg:
                    print("cheating_detected!")
                    game.cheating_detected = True
                if "module_reload" in msg:
                    patchs = msg["module_reload"]
                    game.client_reload_module(patchs)
            game.pkgs_from_server = []

    def deep_reset_level(self, level_name: str): # kstate.should_deep_reset がTrueのときは自前でdeep_resetする
        if not self.is_main_venator or not kstate.should_deep_reset:
            super().deep_reset_level(level_name)
        else:
            self.maps_dict[level_name] = deepcopy(kstate.deepcopy_maps_dict[level_name])

    def setup_map(self):
        self.key_history.clear()
        if not self.is_main_venator:
            super().setup_map()
            return
        if self.net is None and kstate.deepcopy_maps_dict is None: # 最初のsetup_mapをhook
            kstate.deepcopy_maps_dict = deepcopy(self.original_maps_dict)

        super().setup_map()
        
        if "boss" in self.current_map:
            kstate.go_boss = False

        if not kstate.loading_key_history_from and exists_replay(get_autoload_replay_name(self.current_map)):
            kstate.loading_key_history_from = get_autoload_replay_name(self.current_map)

        if kstate.loading_key_history_from:
            key_history, label = load_key_history_from_name(kstate.loading_key_history_from)
            if label == self.current_map:
                kstate.replay_start(key_history, instant=kstate.instant_replay)
                kstate.instant_replay = False
                kstate.loading_key_history_from = None
        else:
            kstate.loaded_key_history = None

    def backup(self, skip_maps_dict=True):
        return VenatorPickler(self).backup(skip_maps_dict)

    def tick_with_keys(self, keys):
        old_tick_stop = kstate.ticking_stop
        kstate.ticking_stop = False
        self.real_pressed_keys = keys.copy()
        self.tick()
        self.real_pressed_keys.clear()
        kstate.ticking_stop = old_tick_stop

    def tick_with_key_history(self, key_history):
        for keys in key_history.iterator():
            self.tick_with_keys(keys)

    def _update_key_history(self):
        if self.is_main_venator and self.screen_fader is not None:
            return
        recording_keys = self.raw_pressed_keys.difference(key_config.keys())
        self.key_history.append(recording_keys)

    def _arcade_cheat(self, pressed_keys):
        pass

    def _pressed_key_hook(self, raw_pressed_keys):
        if self.is_server:
            return raw_pressed_keys
        if self.player is None:
            return raw_pressed_keys
        pressed_keys = raw_pressed_keys.copy()
        pressed_keys |= kstate.locked_key

        if self.screen_fader is None and kstate.loaded_key_history is not None:
            keys = kstate.loaded_key_history.pop()
            pressed_keys |= keys
            kstate.replay_cur += 1
            if kstate.loaded_key_history.length == 0:
                kstate.loaded_key_history = None

        if self.arcade_system is not None:
            if kstate.arcade_game is not None:
                self._arcade_cheat(pressed_keys)
            return pressed_keys

        equipped_weapon = [weapon for weapon in self.player.weapons if weapon.equipped] # スペース長押しで武器を使えるようにする
        if (len(equipped_weapon) == 1
                and equipped_weapon[0].cool_down_timer > 0
                and Keys.SPACE in pressed_keys):
            pressed_keys.remove(Keys.SPACE)

        if kstate.interactive_key_next is not None and self.tics > kstate.interactive_key_last_tic + 3:
            # ダイアログの自動キー送信
            print("Dialogue sending:", kstate.interactive_key_next)
            pressed_keys.add(kstate.interactive_key_next)
            kstate.interactive_key_next = None
            kstate.interactive_key_last_tic = self.tics

        if kstate.auto_painting and self.painting_enabled and self.painting_system is not None:
            pressed_keys |= self._tick_auto_painting()

        if Keys.LSHIFT in pressed_keys:
            if self.player.stamina == 0 or ((Keys.D in pressed_keys) == (Keys.A in pressed_keys)):
                pressed_keys.remove(Keys.LSHIFT)

        if isinstance(self.boss, FightingBoss) and len(equipped_weapon) == 1 and kstate.boss_auto_aim:
            can_shoot = equipped_weapon[0].cool_down_timer == 0 and Keys.SPACE not in self.prev_pressed_keys
            can_shoot_next = equipped_weapon[0].cool_down_timer == 1
            if can_shoot:
                pressed_keys.add(Keys.SPACE)
            if can_shoot_next:
                if self.player.x < self.boss.x and self.player.sprite.flipped:
                    pressed_keys.add(Keys.D)
                    if Keys.A in pressed_keys:
                        pressed_keys.remove(Keys.A)
                if self.player.x > self.boss.x and not self.player.sprite.flipped:
                    pressed_keys.add(Keys.A)
                    if Keys.D in pressed_keys:
                        pressed_keys.remove(Keys.D)

        if key_config["double_jump"] in pressed_keys: # double jumping
            can_double_jump = False
            player_hitbox = Hitbox(self.player.x1, self.player.x2, round(self.player.y1 - 1, 2), round(self.player.y2 - 1, 2))
            _, collisions_y, _ = self.physics_engine._get_collisions_list(player_hitbox)
            for _, mpv in collisions_y:
                if mpv.y > 0:
                    can_double_jump = True
            if can_double_jump:
                pressed_keys.add(Keys.W)
            for o in self.objects:
                left_info, right_info = gameutils.double_jump_alignment(self, self.player, o)
                if left_info is not None and left_info[0] and Keys.D in pressed_keys: # walk if moves right
                    pressed_keys.remove(Keys.D)
                if left_info is not None and left_info[1] and Keys.D in pressed_keys and Keys.LSHIFT in pressed_keys: # walk if moves right
                    pressed_keys.remove(Keys.LSHIFT)
                if left_info is not None and left_info[2] and Keys.D in pressed_keys: # run if moves right
                    pressed_keys.add(Keys.LSHIFT)
                if right_info is not None and right_info[0] and Keys.A in pressed_keys: # stop if moves left
                    pressed_keys.remove(Keys.A)
                if right_info is not None and right_info[1] and Keys.A in pressed_keys and Keys.LSHIFT in pressed_keys: # walk if moves left
                    pressed_keys.remove(Keys.LSHIFT)
                if right_info is not None and right_info[2] and Keys.A in pressed_keys: # run if moves left
                    pressed_keys.add(Keys.LSHIFT)

        if kstate.go_boss and self.current_map == "base":
            pressed_keys.add(Keys.A)


        if Keys.R in pressed_keys: # リセットのタイミングをshoot_timerで揃える
            pressed_keys.remove(Keys.R)
            kstate.reset_delay = True
        if kstate.reset_delay:
            if self.boss is not None:
                resetting = self.tics % 100 == 0
            else:
                shoot_timers = [o.shoot_timer for o in self.objects if isinstance(o, Enemy) and o.can_shoot and not o.dead]
                resetting = len(shoot_timers) == 0 or shoot_timers[0] == 59
            if resetting:
                kstate.reset_delay = False
                pressed_keys.add(Keys.R)

        if self.screen_fader is None and not self.player.dead: # tickを進める場合キー履歴/ゲームのバックアップを保存0
            if self.tics % kstate.backup_rate == 0:
                bu = self.backup(skip_maps_dict=False)
                if bu is not None:
                    kstate.venator_history = kstate.venator_history[:kstate.venator_history_cursor]
                    kstate.venator_history.append(bu)
                    kstate.venator_history_cursor = len(kstate.venator_history)
                if len(kstate.venator_history) > max_venator_history:
                    kstate.venator_history.pop(0)
                    kstate.venator_history_cursor -= 1

        return pressed_keys

    def _painting_pos(self, dx=None, dy=None):
        dot_size = self.painting_system.dot_size
        x = int(self.player.x)
        if dx is not None:
            x += dx
        x = x - x % dot_size
        y = int(self.player.y)
        if dy is not None:
            y += dy
        y = y - y % dot_size
        return x, y

    def _calc_painting_target_image(self): # お絵描きの目標となる絵を生成
        h = 20
        w = 10
        colors = [[0] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                colors[i][j] = (i + 2 * j) % (len(self.painting_system.all_colors) + 1) - 1
        return colors

    def _should_change_color(self, nx, ny):
        bx, by = kstate.auto_painting_base_pos
        dot_size = self.painting_system.dot_size
        colors = self.painting_system.colors
        x, y = nx * dot_size + bx, ny * dot_size + by
        c = colors[x][y].color_id if x in colors and y in colors[x] else -1
        return kstate.painting_target_image[ny][nx] != c

    def _tick_auto_painting(self): # 現在の座標の色が目標と違えばPencilを使う
        dot_size = self.painting_system.dot_size
        bx, by = kstate.auto_painting_base_pos
        px, py = self._painting_pos()
        x, y = (px - bx) // dot_size, (py - by) // dot_size
        keys = set()
        move_next = False
        w = len(kstate.painting_target_image[0])
        h = len(kstate.painting_target_image)
        if not (0 <= x < w and 0 <= y < h):
            return keys
        if self._should_change_color(x, y):
            if Keys.SPACE not in self.prev_pressed_keys:
                keys.add(Keys.SPACE)
        else:
            if any(self._should_change_color(x, i) for i in range(y+1, h)): # move up
                npx, npy = px, py+self.player.base_y_speed
                keys.add(Keys.W)
            elif y != 0: # move down
                npx, npy = px, py-self.player.base_y_speed
                keys.add(Keys.S)
            elif x+1 < w: #move right
                npx, npy = px+self.player.base_x_speed, py
                keys.add(Keys.D)
            else: # end
                return keys
        return keys


class VenatorPickler(pickle.Pickler):
    def __init__(self, venator):
        self.venator = venator
        self.pickle_memo = {}
        self.file = io.BytesIO()
        super().__init__(self.file)

    def persistent_id(self, obj):
        if (isinstance(obj, Wall) and obj.name == "generic_platform") or isinstance(obj, (NetworkConnection, ShapeLayer, SpriteLayer, CombinedLayer, TextureReference, Tileset, GuiImage)):
            self.pickle_memo[id(obj)] = obj
            return id(obj)
        else:
            return None

    def backup(self, skip_maps_dict):
        ignore_attrs = {}
        skip_attrs = VenatorState.skip_attrs.copy()
        if skip_maps_dict:
            skip_attrs += ["maps_dict", "original_maps_dict"]
        for key in skip_attrs:
            ignore_attrs[key] = self.venator.__dict__[key]
            self.venator.__dict__[key] = None
        try:
            self.dump(self.venator)
            succeed = True
        except Exception as e:
            print("backup failed: ", e)
            succeed = False
        for key, val in ignore_attrs.items():
            self.venator.__dict__[key] = val
        if succeed:
            return VenatorState(self.venator.tics, self.file, self.pickle_memo, skip_maps_dict)
        else:
            return None


class VenatorUnpickler(pickle.Unpickler):
    def __init__(self, file, pickle_memo):
        super().__init__(file)
        self.pickle_memo = pickle_memo

    def persistent_load(self, pid):
        return self.pickle_memo[pid]


class VenatorState:
    skip_attrs = ["mutex", "scene_dict", "real_pressed_keys", "arcade_system", "cheating_detected", "pkgs_from_server"]

    def __init__(self, tics, pickled, pickle_memo, skip_maps_dict):
        self.tics = tics
        self.pickled = pickled
        self.pickle_memo = pickle_memo
        self.skip_maps_dict = skip_maps_dict

    def restore(self, game):
        self.pickled.seek(0)
        restored_game = VenatorUnpickler(self.pickled, self.pickle_memo).load()
        skip_attrs = VenatorState.skip_attrs.copy()
        if self.skip_maps_dict:
            skip_attrs += ["maps_dict", "original_maps_dict"]
        for key in skip_attrs:
            restored_game.__dict__[key] = game.__dict__[key]
        restored_game.is_main_venator = False
        return restored_game

    def close(self):
        self.pickled.close()
