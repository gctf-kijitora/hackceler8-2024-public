import game.components.player
import kijitora.kstate as kstate


class HackedPlayer(game.components.player.Player):
    def decrease_health(self, points, source=None):
        if not kstate.invincible:
            super().decrease_health(points, source)
