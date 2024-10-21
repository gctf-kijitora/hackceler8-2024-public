import time

import client
import imgui
import math

from game.engine import gfx
from game.engine.keys import Keys
from game.engine.generics import GenericObject
from game.engine.point import Point
from game.venator import Venator

from game.components.boss.fighting_boss import FightingBoss
from game.components.enemy.enemy import Enemy
from game.components.fire import Fire
from game.components.items import Item
from game.components.player import Player
from game.components.projectile import Projectile
from game.components.portal import Portal
from game.components.weapon.cannon import Cannon
from game.components.weapon.gun import Gun
from game.components.weapon.weapon import Weapon
from game.components.env_element import EnvElement
from game.components.npc.npc import Npc
from game.engine.physics import PhysicsEngine
from game.engine.modifier import HealthDamage
from game.engine.modifier import HealthIncreaser

import kijitora.kstate as kstate
from kijitora.predict import Predictor
import kijitora.gameutils as gameutils


class Color(tuple):
    def alpha(self, alpha):
        return Color((*self[:-1], alpha))


BLACK = Color((0, 0, 0, 255))
RED = Color((255, 0, 0, 255))
GREEN = Color((0, 255, 0, 255))
YELLOW = Color((255, 255, 0, 255))
BLUE = Color((0, 0, 255, 255))
MAGENTA = Color((255, 0, 255, 255))
CYAN = Color((0, 255, 255, 255))
WHITE = Color((255, 255, 255, 255))
BRIGHT_BLACK = Color((128, 128, 128, 255))
BRIGHT_RED = Color((255, 128, 128, 255))
BRIGHT_GREEN = Color((128, 255, 128, 255))
BRIGHT_YELLOW = Color((255, 255, 128, 255))
BRIGHT_BLUE = Color((128, 128, 255, 255))
BRIGHT_MAGENTA = Color((255, 128, 255, 255))
BRIGHT_CYAN = Color((128, 255, 255, 255))
BRIGHT_WHITE = Color((255, 255, 255, 255))
DARK_BLACK = Color((0, 0, 0, 255))
DARK_RED = Color((128, 0, 0, 255))
DARK_GREEN = Color((0, 128, 0, 255))
DARK_YELLOW = Color((128, 128, 0, 255))
DARK_BLUE = Color((0, 0, 128, 255))
DARK_MAGENTA = Color((128, 0, 128, 255))
DARK_CYAN = Color((0, 128, 128, 255))
DARK_WHITE = Color((128, 128, 128, 255))


class DrawUtils:
    main_layer: gfx.CombinedLayer
    predictor: Predictor
    game: Venator | None

    def draw_hitbox(self, hitbox, color):
        if hitbox is None:
            return
        self.main_layer.add(gfx.lrtb_rectangle_outline(hitbox.x1, hitbox.x2, hitbox.y1, hitbox.y2, color, border=2))
        self.main_layer.add(gfx.lrtb_rectangle_filled(hitbox.x1, hitbox.x2, hitbox.y1, hitbox.y2, color.alpha(64)))
        if isinstance(hitbox, GenericObject):
            self.main_layer.add(gfx.circle_filled(hitbox.x, hitbox.y, 2, color))

    def draw_walk_data(self, obj, color):
        cur_x, cur_y = obj.orig_x, obj.orig_y
        for walk_step in obj.walk_data.data:
            if isinstance(walk_step, tuple):
                nxt_x = cur_x
                nxt_y = cur_y
                match walk_step[0]:
                    case "N":
                        nxt_y += walk_step[1]
                    case "E":
                        nxt_x += walk_step[1]
                    case "S":
                        nxt_y -= walk_step[1]
                    case "W":
                        nxt_x -= walk_step[1]
                self.draw_line(cur_x, cur_y, nxt_x, nxt_y, color)
                cur_x = nxt_x
                cur_y = nxt_y
            else:
                self.main_layer.add(gfx.circle_filled(cur_x, cur_y, 3 + math.atan(walk_step) * 2, color))

    # engine/shaders/shapelayer_f.glsl に flags=8 の処理を追記した
    def draw_line(self, x1, y1, x2, y2, color):
        if x1 < x2:
            x1 -= 1
            x2 += 1
        else:
            x1 += 1
            x2 -= 1
        if y1 < y2:
            y1 -= 1
            y2 += 1
        else:
            y1 += 1
            y2 -= 1
        self.main_layer.add(gfx.ShapeDrawParams(x=x1, xr=x2, y=y1, yt=y2, flags=8, border_width=3, color=color))

    def draw_rect(self, x1, x2, y1, y2, color):
        self.main_layer.add(gfx.lrtb_rectangle_filled(x1, x2, y1, y2, color))

    def draw_bar(self, cx, y, p, bar_width, bg_color, fg_color):
        charge_width = round(p*bar_width)
        x1 = cx-bar_width/2
        self.draw_rect(x1, x1+bar_width, y, y+5, bg_color)
        self.draw_rect(x1, x1+charge_width, y, y+5, fg_color)

    def render_hud_for_arcade(self):
        self.camera.update()
        self.camera.use()
        imgui.push_style_color(imgui.COLOR_TEXT, 0,0,0,1)
        if kstate.loading_key_history_from is not None:
            instant_txt = "instant " if kstate.instant_replay else ""
            gfx.draw_txt("loading_key_history_from", gfx.FONT_PIXEL[15], f"{instant_txt}replay loading from {kstate.loading_key_history_from}", 350, -50)
        if kstate.loaded_key_history is not None:
            gfx.draw_txt("loaded_key_replaying", gfx.FONT_PIXEL[20], f"replaying {kstate.replay_cur}/{kstate.replay_total}", 500, -30)

        # 現在のtick / tickrate
        if self.net is None:
            gfx.draw_txt("tick_info", gfx.FONT_PIXEL[30], f"#{self.game.tics}/{gfx.TICKRATE}", 30, -75)
        else:
            gfx.draw_txt("tick_info", gfx.FONT_PIXEL[30], f"#{self.game.tics}/{kstate.last_sent_tick}/{gfx.TICKRATE}", 30, -75)

        # 直近のキー履歴
        for i in range(min(10, len(self.game.key_history.history))):
            keys, tics = self.game.key_history.history[~i]
            keys_str = "".join(sorted(str(key.serialized) for key in keys))
            gfx.draw_txt(f"key_history_{i}", gfx.FONT_PIXEL[15], f"{keys_str:5}:{tics}\n", 10, i * 20)

        cheat_state = []
        if kstate.ticking_stop:
            cheat_state.append("ticking_stop")
        gfx.draw_txt("cheat_state", gfx.FONT_PIXEL[15], ",".join(cheat_state), 30, -125)

        if len(kstate.locked_key) > 0:
            gfx.draw_txt("key_lock", gfx.FONT_PIXEL[15], "KEYLOCK:" + ",".join(map(lambda k: k.serialized, kstate.locked_key)), 30, -100)
        else:
            gfx.draw_txt("key_lock", gfx.FONT_PIXEL[15], "KEYLOCK: OFF", 30, -100)


        imgui.pop_style_color()  # COLOR_TEXT
        self.main_layer.draw()
        self.main_layer.clear()
        self.gui_camera.update()
        self.gui_camera.use()



    def render_hud(self):
        if self.game is None or self.game.player is None:
            return
        if self.game.arcade_system is not None:
            self.render_hud_for_arcade()
            return

        self._center_camera_to_player()
        self.camera.update()
        self.camera.use()

        self.draw_obj_hitboxes()
        if self.game.boss is None:
            self.render_predict_dots()

        if self._white_text():
            imgui.push_style_color(imgui.COLOR_TEXT, 1,1,1,1)
        else:
            imgui.push_style_color(imgui.COLOR_TEXT, 0,0,0,1)

        if isinstance(self.game.boss, FightingBoss):
            b = self.game.boss
            gfx.draw_txt("boss_seed", gfx.FONT_PIXEL[20], f"{kstate.boss_starting_seed}", -800, 25)
            gfx.draw_txt("boss_state", gfx.FONT_PIXEL[20], f"{b.state.name} : {b.state.timer} : {[s for s in b.state.next_states]}", -800, 50)
            for bullet in b.bullets:
                self.main_layer.add(gfx.circle_filled(bullet.x, bullet.y, bullet.radius, RED.alpha(32)))
            box = b.state.slashbox_left if b.sprite.flipped else b.state.slashbox_right
            if box is not None and b.state.slash_timer < 52:
                self.draw_hitbox(box, RED)

        if kstate.auto_painting:
            self.draw_auto_painting_info()

        if kstate.loading_key_history_from is not None:
            instant_txt = "instant " if kstate.instant_replay else ""
            gfx.draw_txt("loading_key_history_from", gfx.FONT_PIXEL[15], f"{instant_txt}replay loading from {kstate.loading_key_history_from}", 350, -80)
        if kstate.loaded_key_history is not None:
            gfx.draw_txt("loaded_key_replaying", gfx.FONT_PIXEL[20], f"replaying {kstate.replay_cur}/{kstate.replay_total}", 500, -60)

        # 現在のtick / tickrate / backup rate
        if self.net is None:
            gfx.draw_txt("tick_info", gfx.FONT_PIXEL[30], f"#{self.game.tics}/{gfx.TICKRATE}/{kstate.backup_rate}", 30, -125)
        else:
            gfx.draw_txt("tick_info", gfx.FONT_PIXEL[30], f"#{self.game.tics}/{kstate.last_sent_tick}/{gfx.TICKRATE}/{kstate.backup_rate}", 30, -125)
            

        # 直近のキー履歴
        for i in range(min(10, len(self.game.key_history.history))):
            keys, tics = self.game.key_history.history[~i]
            keys_str = "".join(sorted(str(key.serialized) for key in keys))
            gfx.draw_txt(f"key_history_{i}", gfx.FONT_PIXEL[15], f"{keys_str:5}:{tics}\n", 10, i * 20)

        if kstate.path_finding_info_min_dists is not None:
            for k, v in kstate.path_finding_info_min_dists.items():
                self.main_layer.add(gfx.circle_filled(k[0], k[1], 2, RED))

        gfx.draw_txt("player_pos", gfx.FONT_PIXEL[20], f"{self.game.player.x:.2f},{self.game.player.y:.2f},{round(self.game.player.x*100)%115}", 30, -175)

        kstate.fps_history.append(time.time())
        if len(kstate.fps_history) >= 20:
            kstate.fps_history.popleft()
            fps = len(kstate.fps_history) / (kstate.fps_history[-1] - kstate.fps_history[0])
            gfx.draw_txt("fps", gfx.FONT_PIXEL[20], f"{fps:.1f}", 30, -200)
        gfx.draw_txt("current_env", gfx.FONT_PIXEL[15], PhysicsEngine.current_mod.name, 150, -200)

        cheat_state = []
        if kstate.invincible:
            cheat_state.append("invincible")
        if kstate.auto_painting:
            cheat_state.append("auto_painting")
        if kstate.ticking_stop:
            cheat_state.append("ticking_stop")
        if kstate.boss_auto_aim:
            cheat_state.append("boss_auto_aim")
        if kstate.should_deep_reset:
            cheat_state.append("deep_reset")
        gfx.draw_txt("cheat_state", gfx.FONT_PIXEL[15], ",".join(cheat_state), 30, -225)
        gfx.draw_txt("sprite", gfx.FONT_PIXEL[15], self.game.player.sprite.get_animation(), 30, -250)

        if len(kstate.locked_key) > 0:
            gfx.draw_txt("key_lock", gfx.FONT_PIXEL[15], "KEYLOCK:" + ",".join(map(lambda k: k.serialized, kstate.locked_key)), 30, -150)
        else:
            gfx.draw_txt("key_lock", gfx.FONT_PIXEL[15], "KEYLOCK: OFF", 30, -150)


        imgui.pop_style_color()  # COLOR_TEXT

        self.main_layer.draw()
        self.main_layer.clear()
        self.gui_camera.update()
        self.gui_camera.use()

    def draw_obj_hitboxes(self):
        p = self.game.player
        if p is None:
            return
        self.draw_hitbox(p, BLUE)

        if p.melee_hitbox:
            self.draw_hitbox(p.melee_hitbox, RED)

        equipped_weapon = [weapon for weapon in p.weapons if weapon.equipped]
        if len(equipped_weapon) == 1:
            c = equipped_weapon[0]
            charge_width = None
            full_charge = False
            if isinstance(equipped_weapon[0], Cannon) and equipped_weapon[0].charging:
                charge_width = min(1,c.charge_amount/180)
                full_charge = c.charge_amount>=180
            if isinstance(equipped_weapon[0], Gun):
                charge_width = 1-c.cool_down_timer/c.COOL_DOWN_DELAY
                full_charge = c.cool_down_timer <= 0
            if charge_width is not None:
                self.draw_bar((p.x1+p.x2)/2, p.y2+19, charge_width, 50, BLACK, RED if full_charge else BRIGHT_RED)

        for env_tile in self.game.physics_engine.env_tiles:
            self.draw_hitbox(env_tile, BRIGHT_BLUE)

        for o in self.game.objects:
            left_double_jump, right_double_jump = gameutils.can_double_jump(self.game, self.game.player, o)
            if o.blocking and (left_double_jump or right_double_jump):
                self.draw_hitbox(o, YELLOW)
                if left_double_jump:
                    self.draw_rect(o.x1+2, (o.x1+o.x2)/2, o.y1, o.y2, BRIGHT_MAGENTA)
                if right_double_jump:
                    self.draw_rect((o.x1+o.x2)/2, o.x2-2, o.y1, o.y2, BRIGHT_MAGENTA)
            elif o.blocking:
                self.draw_hitbox(o, GREEN)
            else:
                self.draw_hitbox(o, MAGENTA)
            if o.walk_data:
                self.draw_walk_data(o, RED)

            if isinstance(o, Item): # プレイヤー -> アイテム
                line_color = YELLOW if o.display_name == "Coin" else RED
                self.draw_line(p.x, p.y, o.x, o.y, line_color)
            if isinstance(o, Npc): # プレイヤー -> アイテム
                self.draw_line(p.x, p.y, o.x, o.y, GREEN)
            if o.modifier and isinstance(o.modifier, HealthDamage):
                self.main_layer.add(gfx.circle_filled(o.x, o.y, o.modifier.min_distance, RED.alpha(32)))
            if o.modifier and isinstance(o.modifier, HealthIncreaser):
                self.main_layer.add(gfx.circle_filled(o.x, o.y, o.modifier.min_distance, GREEN.alpha(32)))
            if isinstance(o, Enemy) and o.can_melee and not o.dead: # 攻撃範囲
                self.draw_rect(o.x-o.melee_range+p.x2-p.x, o.x+o.melee_range+p.x1-p.x, o.y-o.melee_range+p.y2-p.y, o.y+o.melee_range+p.y1-p.y, RED.alpha(64))
            if isinstance(o, Enemy) and o.can_shoot and not o.dead: # 敵のクールダウン
                self.draw_bar((o.x1+o.x2)/2, o.y2+12, o.shoot_timer/60, 50, BLACK, BRIGHT_RED)
                self.main_layer.add(gfx.circle_filled(o.x, o.y, 400, RED.alpha(32)))
            if isinstance(o, Portal):
                self.draw_line(o.x, o.y, o.dest.x, o.dest.y, BLUE)
                if o.usage_limit is not None:
                    for i in range(o.usage_limit - o.usage_count):
                        self.main_layer.add(gfx.circle_outline(o.x+10*i, o.y+20, 5, BLUE))
            if isinstance(o, Enemy):
                self.draw_bar((o.x1+o.x2)/2, o.y2+5, o.health/o.max_health, 50, BLACK, RED)
        self.draw_bar((p.x1+p.x2)/2, p.y2+5, p.health/p.MAX_HEALTH, 50, BLACK, RED)
        self.draw_bar((p.x1+p.x2)/2, p.y2+12, p.stamina/100, 50, DARK_MAGENTA if p.running else BLACK, YELLOW)
        for o in self.game.projectile_system.weapons: # プレイヤー -> 武器
            self.draw_hitbox(o, GREEN)
            self.draw_line(p.x, p.y, o.x, o.y, RED)
        for o in self.game.projectile_system.active_projectiles: # 弾の軌道
            self.draw_hitbox(o, RED)
            if not hasattr(o, "oob_pos"):
                o.oob_pos = self._oob_pos(o)
            ox, oy = o.oob_pos
            self.draw_line(o.x, o.y, ox, oy, RED)

    def _oob_pos(self, o):
        p = Projectile(Point(o.x, o.y), o.x_speed, o.y_speed, o.origin, scale=o.sprite.scale)
        while not p.check_oob(self.game.player) and not self.game.projectile_system._check_collision(p):
            p.update_position()
        return p.x, p.y

    def render_predict_dots(self):
        if kstate.jump_traj_config == "No":
            return
        if self.game.key_history.length == 0:
            return
        if self.game.player.immobilized:
            return


        keys, tics = self.game.key_history.history[-1]
        if kstate.jump_traj_config == "Stop" and len(keys) > 0:
            return

        if kstate.jump_traj_config == "Stop" and self.game.player.in_the_air:
            return


        if kstate.last_predict_hash != self.game.player.hash:
            kstate.last_predict_hash = self.game.player.hash
            if not self.predictor.init_state(self.game):
                return
        else:
            self.predictor.reset_state()

        self.predictor.key_press(Keys.LSHIFT)
        if not self.game.player.in_the_air:
            self.predictor.key_press(Keys.W)

        direction = self.game.player.direction
        if direction == Player.DIR_W:
            self.predictor.key_press(Keys.A)
        elif direction == Player.DIR_E:
            self.predictor.key_press(Keys.D)

        history, key_history = self.predictor.leap_grounded(gfx.TICKRATE * 5)

        kstate.predict_key_history = key_history

        for i in range(len(history) - 1):
            ax, ay = history[i]
            bx, by = history[i + 1]
            self.draw_line(ax, ay, bx, by, GREEN)


    def draw_auto_painting_info(self): # 目標画像に一致しているドットにハイライト
        if self.game.painting_enabled and self.game.painting_system is not None:
            cx, cy = self.game._painting_pos()
            bx, by = kstate.auto_painting_base_pos
            dot_size = self.game.painting_system.dot_size
            colors = self.game.painting_system.colors
            width = len(kstate.painting_target_image[0])
            height = len(kstate.painting_target_image)
            self.main_layer.add(gfx.rectangle_outline(cx, cy, dot_size, dot_size, GREEN, border=1))
            for ny in range(height):
                for nx in range(width):
                    x, y = bx + nx * dot_size, by + ny * dot_size
                    c = colors[x][y].color_id if x in colors and y in colors[x] else -1
                    if kstate.painting_target_image[ny][nx] == c:
                        self.main_layer.add(gfx.rectangle_outline(x, y, dot_size, dot_size, WHITE, border=1))
            ofs = dot_size/2
            self.main_layer.add(gfx.lrtb_rectangle_outline(bx-ofs, bx+dot_size*width-ofs, by-ofs, by+dot_size*height-ofs, RED, border=1))
