import game.components.flags
import kijitora.kstate as kstate


class HackedFlags(game.components.flags.Flags):
    def stars(self):
        if kstate.gui.net is None: # 適当にデカい値にするとボス部屋を強制開放できる
            return super().stars() + kstate.cheat_stars
        else:
            return super().stars()
