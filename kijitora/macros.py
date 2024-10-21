from kijitora.gameutils import gen_key_history
from game.components.weapon.gun import Gun
import kijitora.kstate as kstate
from game.engine.keys import Keys

def comma_key_pressed():
    print("comma_key_pressed")
    game = kstate.gui.game
    fire_all_guns(game)
    pass

def period_key_pressed():
    print("period_key_pressed")
    game = kstate.gui.game
    pass

def fire_all_guns(game):
    equipped_idx = [i for i, weapon in enumerate(game.player.weapons) if weapon.equipped]
    if len(equipped_idx) == 1:
        equipped_idx = equipped_idx[0]
        table_is_gun = [isinstance(o, Gun) for o in game.player.weapons]
        num_guns_up = sum(table_is_gun[:equipped_idx+1])
        num_guns_down = sum(table_is_gun[equipped_idx:])
        key_history = []
        if num_guns_up < num_guns_down: # scroll down
            num_scroll = 0
            for is_gun in table_is_gun[equipped_idx:]:
                if is_gun:
                    if num_scroll > 0:
                        key_history += [[Keys.P]] + [[Keys.S], []] * (num_scroll - 1) + [[Keys.S], [Keys.P]]
                    key_history.append([Keys.SPACE])
                    num_scroll = 1
                else:
                    num_scroll += 1
            kstate.replay_start(gen_key_history(key_history), overwrite=False)
        else: # scroll up
            num_scroll = 0
            for is_gun in reversed(table_is_gun[:equipped_idx+1]):
                if is_gun:
                    if num_scroll > 0:
                        key_history += [[Keys.P]] + [[Keys.W], []] * (num_scroll - 1) + [[Keys.W], [Keys.P]]
                    key_history.append([Keys.SPACE])
                    num_scroll = 1
                else:
                    num_scroll += 1
            kstate.replay_start(gen_key_history(key_history), overwrite=False)