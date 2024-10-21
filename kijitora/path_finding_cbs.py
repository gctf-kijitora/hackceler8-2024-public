import json
import math
import heapq
import os
import secrets
import time
from game.engine.keys import Keys

search = None
def init_search():
    global search
    if search is not None: return
    print("importing search engines...")
    try:
        search = __import__("search")
    except:
        print("[!] error while importing the search library. try after building and installing the library")
        search = None
        return
    print("done")
 

from kijitora.gameutils import gen_key_history

search_settings = {
    "timeout": 5,                     # Timeout for pathfinding in seconds
    "validate_transitions": False,    # Validate transitions
    "always_shift": True,             # Always shift when pathfinding
    "disable_shift": False,           # Disable shift when pathfinding
    "allowed_moves": "",              # Comma-separated list of moves to allow
    "heuristic_weight": 2.0,          # Weight of heuristic in A*
    "simple_geometry": True,          # Use simple geometry for pathfinding
    "state_batch_size": 16384,        # Number of states to process in batch
    "allow_damage": False,            # Allow taking damage
    "damage_optimization_level": 5,   # Number of times to optimize damage
    "damage_optimization_timeout": 1, # Timeout for damage optimization iteration
}

def get_settings():
    return json.loads(open("cheats-rust/search_settings.json", "r").read())
    # return search_settings # TODO

def search_move_to_keys(move, shift):
    moves = set()
    match move:
        case search.Move.W:
            moves = {Keys.W}
        case search.Move.A:
            moves = {Keys.A}
        case search.Move.D:
            moves = {Keys.D}
        case search.Move.WA:
            moves = {Keys.W, Keys.A}
        case search.Move.WD:
            moves = {Keys.W, Keys.D}
        case search.Move.S:
            moves = {Keys.S}
        case search.Move.SA:
            moves = {Keys.S, Keys.A}
        case search.Move.SD:
            moves = {Keys.S, Keys.D}
        case search.Move.NONE:
            moves = set()
        case _:
            print("unknown move", move)
            return []

    if shift:
        moves.add(Keys.LSHIFT)
    return list(moves)


def _dump_rust_state(game, enable_portals: bool, enable_proj: bool):
    mode = None
    player = game.player
    mode = search.GameMode.Platformer

    cheat_settings = get_settings()
    allowed_moves = []
    if cheat_settings["allowed_moves"].lower() not in {"", "all"}:
        moves = cheat_settings["allowed_moves"].upper().split(",")
        for move in moves:
            allowed_moves.append(getattr(search.Move, move))

    settings = search.SearchSettings(
        mode=mode,
        timeout=cheat_settings["timeout"],
        always_shift=cheat_settings["always_shift"],
        disable_shift=cheat_settings["disable_shift"],
        allowed_moves=allowed_moves,
        heuristic_weight=cheat_settings["heuristic_weight"],
        simple_geometry=cheat_settings["simple_geometry"],
        state_batch_size=cheat_settings["state_batch_size"],
        allow_damage=cheat_settings["allow_damage"],
    )
    static_objects = [
        (
            search.Hitbox(
                search.Rectangle(o.x1, o.x2, o.y1, o.y2),
            ),
            search.ObjectType.Wall()
        )
        for o in (
            game.objects + 
            game.stateful_objects
        )
        if (
            o.nametype == "Wall" or 
            (o.nametype == "Enemy" and o.name == "block_enemy" and not o.dead)
        )
    ]

    deadly_objects_type = {}

    if enable_portals:
        deadly_objects_type["warp"] = search.ObjectType.Warp()
        deadly_objects_type["Portal"] = search.ObjectType.Portal()

    allowed_damage_objects_type = set()
    if cheat_settings["allow_damage"] and not enable_proj:
        allowed_damage_objects_type = {"Ouch", "SpikeOuch"}
    else:
        deadly_objects_type["Ouch"] = search.ObjectType.Ouch()
        deadly_objects_type["SpikeOuch"] = search.ObjectType.SpikeOuch()

    static_objects += [
        (
            search.Hitbox(
                search.Rectangle(o.x1, o.x2, o.y1, o.y2),
            ),
            search.ObjectType.ConstantDamage(o.modifier.damage)
        )
        for o in game.objects
        if o.nametype in allowed_damage_objects_type
    ]
    static_objects += [
        (
            search.Hitbox(
                search.Rectangle(o.x1, o.x2, o.y1, o.y2),
            ),
            deadly_objects_type[o.nametype]
        )
        for o in game.objects + game.stateful_objects
        if o.nametype in deadly_objects_type
    ]
    
    if enable_proj:
        projs = [
            (
                search.Hitbox(
                    search.Rectangle(o.x1, o.x2, o.y1, o.y2),
                ),
                search.ObjectType.Projectile(search.Pointf(getattr(o, 'x_speed', 0), getattr(o, 'y_speed', 0)))
            )
            for o in game.projectile_system.active_projectiles
            if o.nametype in {"Projectile"}
        ]
        static_objects += projs

    environments = [
        search.EnvModifier(
            hitbox=search.Hitbox(
                search.Rectangle(o.x1, o.x2, o.y1, o.y2),
            ),
            name=o.modifier.name,
            jump_speed=o.modifier.jump_speed,
            walk_speed=o.modifier.walk_speed,
            gravity=o.modifier.gravity,
            jump_override=o.modifier.jump_override,
        )
        for o in game.physics_engine.env_tiles
    ]

    # Add generic env to fallback to.
    environments = [
        search.EnvModifier(
            hitbox=search.Hitbox(
                search.Rectangle(0, 0, 0, 0),
            ),
            name="generic",
            jump_speed=1.0,
            walk_speed=1.0,
            gravity=1.0,
            jump_override=False,
        )
    ] + environments

    player_direction = None
    match player.direction:
        case player.DIR_N:
            player_direction = search.Direction.N
        case player.DIR_E:
            player_direction = search.Direction.E
        case player.DIR_S:
            player_direction = search.Direction.S
        case player.DIR_W:
            player_direction = search.Direction.W

    static_state = search.StaticState(
        objects=static_objects,
        environments=environments,
    )

    initial_state = search.PhysState(
        player=search.PlayerState(
            x=player.x,
            y=player.y,

            vx=player.x_speed,
            vy=player.y_speed,
            base_vx=player.base_x_speed,
            base_vy=player.base_y_speed,

            health=player.health,

            jump_override=player.jump_override,
            direction=player_direction,
            in_the_air=player.in_the_air,
            can_jump=player.can_jump,
            running=player.running,
            stamina=player.stamina,

            speed_multiplier=player.speed_multiplier,
            jump_multiplier=player.jump_multiplier,
        ),
        settings=settings.physics_settings(),
        state=static_state,
    )
    return settings, initial_state, static_state


def navigate(venator, dst_pos):
    init_search()
    if search is None:
        return None, {}

    target_x, target_y = dst_pos
    player = venator.player

    settings, initial_state, static_state = _dump_rust_state(venator, True, True)
    target_state = search.PhysState(
        player=search.PlayerState(
            x=target_x,
            y=target_y,

            vx=player.x_speed,
            vy=player.y_speed,
            base_vx=player.base_x_speed,
            base_vy=player.base_y_speed,

            health=player.health,

            jump_override=player.jump_override,
            direction=search.Direction.N,
            in_the_air=player.in_the_air,
            can_jump=player.can_jump,
            running=player.running,
            stamina=player.stamina,

            speed_multiplier=player.speed_multiplier,
            jump_multiplier=player.jump_multiplier,
        ),
        settings=settings.physics_settings(),
        state=static_state,
    )

    cheat_settings = get_settings()

    path = search.astar_search(
        settings=settings,
        initial_state=initial_state,
        target_state=target_state,
        static_state=static_state,
    )

    if (
        path and 
        cheat_settings["allow_damage"] and 
        (level := cheat_settings["damage_optimization_level"]) > 0
    ):
        settings.timeout = cheat_settings["damage_optimization_timeout"]
        l, r = 0, player.health
        for _ in range(level):
            m = (l + r) / 2
            initial_state.set_player_health(m)
            m_path = search.astar_search(
                settings=settings,
                initial_state=initial_state,
                target_state=target_state,
                static_state=static_state,
            )
            if m_path:
                print(f"{m=}, path found")
                r = m
                path = m_path
            else:
                print(f"{m=}, path not found")
                l = m
    
    if not path:
        print("Path not found")

        tmp_dir = os.path.join("/tmp", secrets.token_urlsafe(16))
        os.makedirs(tmp_dir)
        settings_path = os.path.join(tmp_dir, "settings.json")
        initial_state_path = os.path.join(tmp_dir, "initial_state.json")
        target_state_path = os.path.join(tmp_dir, "target_state.json")
        static_state_path = os.path.join(tmp_dir, "static_state.json")

        with open(settings_path, "w") as f:
            f.write(search.serialize_settings(settings))
        with open(initial_state_path, "w") as f:
            f.write(search.serialize_state(initial_state))
        with open(target_state_path, "w") as f:
            f.write(search.serialize_state(target_state))
        with open(static_state_path, "w") as f:
            f.write(search.serialize_static_state(static_state))

        print(f"Path not found, saved to {tmp_dir}")
        return None, {}
    else:
        fake_min_dists = {}
        key_history = []
        for move, shift, state in path:
            fake_min_dists[(state.x, state.y)] = 0
            
            key_history.append(search_move_to_keys(move, shift))
        return gen_key_history(key_history), fake_min_dists

