from collections import deque
from kijitora.keyhistory import KeyHistory
from game.map.tilemap import TileMap

def gen_key_history(keys): # gen_key_history([[Keys.A], [Keys.S, Keys.D]])
    return KeyHistory(deque([(set(k), 1) for k in keys])).compressed()

def can_double_jump(game, player, hitbox):
    if player.last_ground_pos is None:
        return False, False
    px, py = player.x, player.y
    subpixel_left = round((px - 24) * 100) % 115
    subpixel_right = round((px + 24) * 100) % 115
    hitbox_left_subpixel = round(hitbox.x1 * 100) % 115
    hitbox_right_subpixel = round(hitbox.x2 * 100) % 115
    y = round((py - 26) * 100)
    hitbox_y2 = round(hitbox.y2 * 100)
    base_y_speed = round(player.base_y_speed * 100)
    y_speed = round(player.y_speed * 100)
    if y_speed == 0:
        y_speed = base_y_speed
    elif y_speed < base_y_speed:
        cnt = (base_y_speed - y_speed) // 10
        y -= cnt * (base_y_speed + y_speed+10) // 2
        y_speed = base_y_speed
    if hitbox_y2 < y:
        return False, False
    while y_speed > 0 and y + y_speed - 100 <= hitbox_y2:
        y += y_speed
        y_speed -= 10
    y_mpv = hitbox_y2 - (y - 100)
    left_mpv = (subpixel_right - hitbox_left_subpixel) % 115
    right_mpv = (hitbox_right_subpixel - subpixel_left) % 115
    left_ok = left_mpv < 100 and y_mpv < left_mpv
    right_ok = right_mpv < 100 and y_mpv < right_mpv
    return left_ok, right_ok

def double_jump_alignment(game, player, hitbox):
    left_ok, right_ok = can_double_jump(game, player, hitbox)
    cur_player_x1 = round(player.x1 * 100)
    cur_player_x2 = round(player.x2 * 100)
    cur_hitbox_x1 = round(hitbox.x1 * 100)
    cur_hitbox_x2 = round(hitbox.x2 * 100)
    should_stop_left = cur_hitbox_x1 < cur_player_x2 < cur_hitbox_x1+100
    should_stop_right = cur_hitbox_x2-100 < cur_player_x1 < cur_hitbox_x2
    should_walk_left = cur_hitbox_x1 < cur_player_x2+230 < cur_hitbox_x1+100
    should_walk_right = cur_hitbox_x2-100 < cur_player_x1-230 < cur_hitbox_x2
    should_run_left = cur_hitbox_x1 < cur_player_x2+345 < cur_hitbox_x1+100
    should_run_right = cur_hitbox_x2-100 < cur_player_x1-345 < cur_hitbox_x2
    left_info = (should_stop_left, should_walk_left, should_run_left) if left_ok else None
    right_info = (should_stop_right, should_walk_right, should_run_right) if right_ok else None
    return left_info, right_info
