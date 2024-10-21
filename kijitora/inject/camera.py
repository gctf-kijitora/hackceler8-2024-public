import game.engine.gfx
from pyrr import Vector3, Matrix44
import kijitora.kstate as kstate


class HackedCamera(game.engine.gfx.Camera):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.zoom = 1

    def update(self):
        real_pos = self.position / Vector3([
            self.zoom * self.viewport_width / 2,
            self.zoom * self.viewport_height / 2,
            1
        ])
        self.view_matrix = ~Matrix44.from_translation(real_pos)
        self.projection_matrix = Matrix44.orthogonal_projection(0, self.viewport_width * self.zoom, 0, self.viewport_height * self.zoom, -1, 1)

    def move_to(self, pos):
        zoom = 1.1 ** kstate.camera_zoom
        new_x = pos[0] + kstate.camera_offset_x - self.viewport_width / 2 * (zoom - 1)
        new_y = pos[1] + kstate.camera_offset_y - self.viewport_height / 2 * (zoom - 1)
        self.zoom = zoom

        super().move_to((new_x, new_y))
