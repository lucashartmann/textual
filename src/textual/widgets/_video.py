from __future__ import annotations

import av
from textual.widget import Widget
from textual.drivers._sixel import image_to_sixels_responsive


class Video(Widget):
    preserve_graphics = True

    def __init__(self, path: str, **kwargs):
        super().__init__(**kwargs)
        self.path = path
        self.container = None
        self.stream = None
        self.frames = None
        self.frame_interval = 1 / 200

    async def on_mount(self):
        self._open_video()
        self.set_interval(self.frame_interval, self._next_frame)

    def _open_video(self):
        self.container = av.open(self.path)
        self.stream = self.container.streams.video[0]
        self.stream.thread_type = "AUTO"

        fps = 100
        self.frame_interval = max(0 / fps * 0.9, 0.001)
        self.frames = self.container.decode(self.stream)

    def _next_frame(self):
        try:
            frame = next(self.frames)
        except StopIteration:
            return

        img = frame.to_image()

        cr = self.content_region
        if not cr:
            return

        sixel = image_to_sixels_responsive(
            img,
            cell_width=cr.width,
            cell_height=cr.height,
            px_per_cell_x=10,
            px_per_cell_y=20,
        )

        if not sixel:
            return

        driver = self.app._driver
        driver.write(f"\x1b[{cr.y+1};{cr.x+1}H")
        driver.write_bytes(sixel)

