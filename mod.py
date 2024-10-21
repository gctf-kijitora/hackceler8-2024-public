#!/usr/bin/env python3
import sys
from pwn import listen
import threading
import kijitora.inject # DO NOT DELETE THIS LINE
import argparse

import logging
import time
from pyrr.matrix44 import apply_to_vector
from pyrr import Vector3, Matrix44
import imgui

import client
from kijitora.webserver.main import run_server
import moderngl_window as mglw
from game.engine.keys import Keys
from game.engine import gfx
from game.constants import SCREEN_WIDTH, SCREEN_HEIGHT

import kijitora.kstate as kstate
from kijitora.keys import get_keycode
from kijitora.config import get_key_remap, key_config, setup_key_remap, tick_rate_table, replay_slots, savestate_slots, interactive_port
from kijitora.drawutils import DrawUtils
# from kijitora.path_finding import navigate
from kijitora.path_finding_cbs import navigate
from kijitora.keyhistory import save_key_history, load_key_history_from_name
from kijitora.predict import Predictor
from kijitora import macros


class HackedHx8Client(client.Hx8Client, DrawUtils):
    def __init__(self, *args, **kwargs):
        kstate.gui = self
        super().__init__(*args, **kwargs)
        self.x_range = (0, SCREEN_WIDTH)
        self.y_range = (0, SCREEN_HEIGHT)
        self.mouse_pos = (0, 0)
        self.predictor = Predictor()
        kstate.should_deep_reset = self.net is None
        kstate.cheat_stars = self.argv.stars
        kstate.go_boss = self.argv.go_boss

    @classmethod
    def add_arguments(cls, parser: argparse.ArgumentParser):
        client.Hx8Client.add_arguments(parser)
        parser.add_argument(
            '--stars', nargs='?', type=int, default=0, help='Initial stars'
        )
        parser.add_argument(
            '--go-boss',
            action='store_true',
            default=False,
        )

    def setup_game(self):
        super().setup_game()
        self.setup_webserver()
        if self.net is not None:
            self.gui_setup_client()

    def setup_webserver(self):
        setup_key_remap()
        threading.Thread(target=run_server, args=(self,), daemon=True).start()

    def gui_setup_client(self):
        pass

    def render(self, time: float, frame_time: float):
        self._handle_kijitora_commands()

        imgui.new_frame()
        self.tick_accumulator += frame_time
        if self.tick_accumulator >= 1.0/gfx.TICKRATE:
            tick_cnt = 0
            while self.tick_accumulator >= 1.0/gfx.TICKRATE:
                self.tick_accumulator -= 1.0/gfx.TICKRATE
                tick_cnt += 1
            for _ in range(min(tick_cnt, 5)): # renderごとに最大5tickまで進める
                self.tick(1.0/gfx.TICKRATE)
        self.draw()
        imgui.end_frame()
        imgui.render()
        self.imgui.render(imgui.get_draw_data())
        self.draw_fader()

    def _handle_replay_command(self, extra_newly_pressed_keys):
        game = self.game
        for keyname in replay_slots:
            if get_keycode(keyname) not in extra_newly_pressed_keys: continue
            # ctrlが押されていたらロード, 押されていなかったらセーブ
            if kstate.ctrl_pressed:
                if keyname in kstate.key_history_slots:
                    del kstate.key_history_slots[keyname]
            else:
                if keyname in kstate.key_history_slots:
                    kstate.instant_replay = kstate.alt_pressed
                    kstate.loading_key_history_from = kstate.key_history_slots[keyname]
                    _, label = load_key_history_from_name(kstate.loading_key_history_from)
                    kstate.reset_delay = label == game.current_map
                elif game.arcade_system is None:
                    save_key_history(game.current_map, game.key_history, keyname, game.tics)
                else:
                    save_key_history("arcade", game.key_history, keyname, game.tics)
            break

    def _handle_kijitora_commands(self):
        game = self.game
        if game is None:
            return
        if game.is_server:
            return
        pressed_keys = game.real_pressed_keys.copy()
        newly_pressed_keys = pressed_keys.difference(kstate.prev_pressed_keys)
        extra_newly_pressed_keys = kstate.extra_real_pressed_key.difference(kstate.extra_prev_pressed_key)
        if key_config["reserved_comma"] in extra_newly_pressed_keys:
            macros.comma_key_pressed()
        if key_config["reserved_period"] in extra_newly_pressed_keys:
            macros.period_key_pressed()
        if game.get_text_input() is None:
            self._handle_replay_command(extra_newly_pressed_keys)
            if key_config["dec_tick_rate"] in newly_pressed_keys: # tickrate変更
                if kstate.alt_pressed:
                    kstate.backup_rate = max(1, kstate.backup_rate - 1)
                else:
                    gfx.TICKRATE = tick_rate_table[max(0, tick_rate_table.index(gfx.TICKRATE) - 1)]
            if key_config["inc_tick_rate"] in newly_pressed_keys:
                if kstate.alt_pressed:
                    kstate.backup_rate = kstate.backup_rate + 1
                else:
                    gfx.TICKRATE = tick_rate_table[min(len(tick_rate_table) - 1, tick_rate_table.index(gfx.TICKRATE) + 1)]
                    if game.net is not None and any(["hackceler8-2024.ctfcompetition.com" in val for val in sys.argv]):
                        gfx.TICKRATE = min(gfx.TICKRATE, 60)
            if key_config["stop_key_replay"] in newly_pressed_keys: # キー履歴ロードを停止
                kstate.loaded_key_history = None

            if key_config["toggle_stop_tick"] in newly_pressed_keys: # tick停止
                kstate.ticking_stop = not kstate.ticking_stop
            if key_config["advance_tick"] in pressed_keys and kstate.tick_advance_cooltime <= 0: # 1tick進める
                kstate.tick_advance = True
                kstate.tick_advance_cooltime = 10
            else:
                kstate.tick_advance_cooltime -= 1
            if key_config['key_lock'] in newly_pressed_keys:
                if len(kstate.locked_key) == 0:
                    kstate.locked_key = game.real_pressed_keys - { key_config['key_lock'] }
                else:
                    kstate.locked_key.clear()
        if game.arcade_system is None:
            if game.get_text_input() is None:
                if key_config["camera_reset"] in pressed_keys:
                    kstate.camera_offset_x = 0
                    kstate.camera_offset_y = 0
                    kstate.camera_zoom = 0
                if key_config["camera_zoom_in"] in pressed_keys: # カメラズーム
                    kstate.camera_zoom -= 1
                if key_config["camera_zoom_out"] in pressed_keys:
                    kstate.camera_zoom += 1
                if game.net is None: # only standalone mode
                    for keyname in savestate_slots:
                        if get_keycode(keyname) not in extra_newly_pressed_keys: continue
                        # ctrlが押されていたらロード, 押されていなかったらセーブ
                        if kstate.ctrl_pressed:
                            if keyname in kstate.game_backups:
                                del kstate.game_backups[keyname]
                        else:
                            if keyname not in kstate.game_backups:
                                start = time.time()
                                kstate.game_backups[keyname] = (game.backup(skip_maps_dict=False), time.time())
                                print("backup saved", time.time() - start)
                            else:
                                kstate.restoring_game = kstate.game_backups[keyname][0]
                        break
                    if key_config["toggle_deep_reset"] in newly_pressed_keys:
                        kstate.should_deep_reset = not kstate.should_deep_reset
                    if key_config["toggle_invincible"] in newly_pressed_keys: # 無敵
                        kstate.invincible = not kstate.invincible
                    if key_config["boss_auto_aim"] in newly_pressed_keys:
                        kstate.boss_auto_aim = not kstate.boss_auto_aim
                        
                if key_config["tick_undo"] in newly_pressed_keys:
                    if 0 <= kstate.venator_history_cursor - 1 < len(kstate.venator_history):
                        if kstate.venator_history[kstate.venator_history_cursor - 1].tics >= kstate.last_sent_tick:
                            print("undo")
                            kstate.venator_history_cursor -= 1
                            kstate.restoring_game = kstate.venator_history[kstate.venator_history_cursor]
                            kstate.ticking_stop = True
                if key_config["tick_redo"] in newly_pressed_keys:
                    if 0 <= kstate.venator_history_cursor + 1 < len(kstate.venator_history):
                        if kstate.venator_history[kstate.venator_history_cursor + 1].tics >= kstate.last_sent_tick:
                            print("redo")
                            kstate.venator_history_cursor += 1
                            kstate.restoring_game = kstate.venator_history[kstate.venator_history_cursor]
                            kstate.ticking_stop = True
                if key_config["toggle_auto_paint"] in newly_pressed_keys:
                    if kstate.auto_painting:
                        kstate.auto_painting = False
                    elif game.painting_enabled and game.painting_system is not None:
                        kstate.auto_painting = True
                        kstate.auto_painting_base_pos = game._painting_pos()
                        kstate.painting_target_image = game._calc_painting_target_image()
                kstate.auto_painting = kstate.auto_painting and game.painting_enabled and game.painting_system is not None

                if key_config["predict_move"] in newly_pressed_keys:
                    kstate.loaded_key_history = kstate.predict_key_history

                if key_config['jump_traj'] in newly_pressed_keys:
                    print(f'{kstate.jump_traj_config=}')
                    if kstate.jump_traj_config == "No":
                        kstate.jump_traj_config = "Stop"
                    elif kstate.jump_traj_config == "Stop":
                        kstate.jump_traj_config = "Always"
                    elif kstate.jump_traj_config == "Always":
                        kstate.jump_traj_config = "No"


            if kstate.ctrl_pressed and Keys.S in newly_pressed_keys: # Ctrl+S -> Interactive textbox
                if kstate.interactive_sock is not None: # Stop interactive mode
                    print("[+] Shutting down interactive mode")
                    kstate.interactive_sock = None
                else:
                    print(f"[+] Listening on {interactive_port}...")
                    kstate.interactive_sock = listen(interactive_port)
                    kstate.interactive_sock.wait_for_connection()
                    kstate.interactive_received = False
                    print("[+] Connection accepted!")

            if game.get_text_input() is not None:
                if kstate.ctrl_pressed and Keys.V in newly_pressed_keys:
                    kstate.paste_text = input("paste:")

            if kstate.teleport_pos is not None:
                x, y = kstate.teleport_pos
                x = (x // 1.15) * 1.15 + game.player.x % 1.15
                game.player.place_at(x, y)
                kstate.camera_offset_x = 0
                kstate.camera_offset_y = 0
                kstate.teleport_pos = None
            if kstate.path_finding_dest_pos is not None:
                x, y = kstate.path_finding_dest_pos
                navigate_result, min_dists = navigate(game, kstate.path_finding_dest_pos)
                kstate.path_finding_info_min_dists = min_dists
                if navigate_result is not None:
                    kstate.replay_start(navigate_result)
                kstate.path_finding_dest_pos = None


        kstate.prev_pressed_keys = pressed_keys.copy()
        kstate.extra_prev_pressed_key = kstate.extra_real_pressed_key.copy()

    def tick(self, _delta_time):
        if self.game and kstate.restoring_game is not None:
            start = time.time()
            self.game.is_main_venator = False
            self.game = kstate.restoring_game.restore(self.game)
            self.game.is_main_venator = True
            print("backup restored", time.time() - start)
            kstate.restoring_game = None
        for task in kstate.next_tick_tasks:
            task(self.game)
        kstate.next_tick_tasks.clear()

        super().tick(_delta_time)

    def draw(self):
        super().draw()

        self.render_hud()


    def camera_pos(self, x, y):
        return ((x - self.x_range[0]) / self.scale, (y - self.y_range[0]) / self.scale)

    def on_resize(self, width, height):
        x_offset = max(0, (width - height * SCREEN_WIDTH / SCREEN_HEIGHT) / 2)
        y_offset = max(0, (height - width * SCREEN_HEIGHT / SCREEN_WIDTH) / 2)
        self.x_range = (x_offset, width - x_offset)
        self.y_range = (y_offset, height - y_offset)

        super().on_resize(width, height)

    def mouse_position_event(self, x, y, dx, dy):
        self.mouse_pos = self.camera_pos(x, y)

        super().mouse_position_event(x, y, dx, dy)

    def mouse_press_event(self, x, y, button):
        cpos = self.camera_pos(x, y)
        is_inner_window = self.x_range[0] <= x <= self.x_range[1] and self.y_range[0] <= y <= self.y_range[1]
        if self.camera.view_matrix is not None and is_inner_window: # right click
            temp_x, temp_y, _ = apply_to_vector(Matrix44.orthogonal_projection(0, self.camera.viewport_width, 0, self.camera.viewport_height, -1, 1), Vector3([cpos[0], cpos[1], 0]))
            dest_x, dest_y, _ = apply_to_vector((self.camera.view_matrix * self.camera.projection_matrix).inverse, Vector3([temp_x, -temp_y, 0]))
            if button == 2 and self.net is None:
                kstate.teleport_pos = (dest_x, dest_y)
            if button == 3:
                kstate.path_finding_dest_pos = (dest_x, dest_y)

        super().mouse_press_event(x, y, button)

    def mouse_scroll_event(self, x_offset, y_offset):
        zoom_diff = 1.1 ** (kstate.camera_zoom - y_offset) - 1.1 ** kstate.camera_zoom
        kstate.camera_offset_x -= (self.mouse_pos[0] - self.camera.viewport_width / 2) * zoom_diff
        kstate.camera_offset_y += (self.mouse_pos[1] - self.camera.viewport_height / 2) * zoom_diff
        kstate.camera_zoom -= y_offset

        super().mouse_scroll_event(x_offset, y_offset)

    def mouse_drag_event(self, x, y, dx, dy):
        kstate.camera_offset_x -= dx / self.scale * (1.1 ** kstate.camera_zoom)
        kstate.camera_offset_y += dy / self.scale * (1.1 ** kstate.camera_zoom)

        super().mouse_drag_event(x, y, dx, dy)

    def on_key_press(self, symbol: int, _modifiers: int):
        if self.game is None:
            return
        kstate.ctrl_pressed |= symbol == 65507
        kstate.alt_pressed |= symbol == 65513
        symbol = get_key_remap().get(symbol, symbol)
        k = Keys.from_ui(symbol)
        if k:
            self.game.real_pressed_keys.add(k)
        else:
            kstate.extra_real_pressed_key.add(symbol)


    def on_key_release(self, symbol: int, _modifiers: int):
        if self.game is None:
            return

        kstate.ctrl_pressed &= symbol != 65507
        kstate.alt_pressed &= symbol != 65513
        symbol = get_key_remap().get(symbol, symbol)
        k = Keys.from_ui(symbol)
        if k:
            if k in self.game.real_pressed_keys:
                self.game.real_pressed_keys.remove(k)
        else:
            if symbol in kstate.extra_real_pressed_key:
                kstate.extra_real_pressed_key.remove(symbol)


def main():
    logging.getLogger('PIL').setLevel(logging.WARNING)
    mglw.run_window_config(HackedHx8Client)


if __name__ == '__main__':
    main()
