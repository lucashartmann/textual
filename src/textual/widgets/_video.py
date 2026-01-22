import av
from PIL import Image as PILImage
from textual import events, log, on
from textual.drivers.graphics import GraphicsCommand
from textual.drivers.image_render import RenderType, get_renderer, draw
from textual.widgets._graphic import Graphic


class Video(Graphic):

    preserve_graphics = True

    def __init__(
        self,
        path: str,
        render_type: RenderType = RenderType.AUTO,
        fps: int = 60,
        loop: bool = True,
        autoplay: bool = False,
        low_latency: bool = False,
        preload_frames: bool = False,
        **kwargs,
    ):
        super().__init__(render_type=render_type, **kwargs)

        self.path = path
        self.target_fps = fps
        self.loop = loop
        self.autoplay = autoplay
        self.low_latency = low_latency
        self.preload_frames = preload_frames

        self.container = None
        self.stream = None
        self.frames = None

        self.preloaded_frames: list[PILImage.Image] = []
        self.current_frame_index = 0
        self.current_frame_pil: PILImage.Image | None = None
        self.thumbnail: PILImage.Image | None = None

        self.is_playing = False

        self.video_fps = 0.0
        self.frame_count = 0
        self.duration = 0.0

        self.frame_interval = 1.0 / fps if fps > 0 else 0.001
        self._timer = None

        self._renderer = None
        self._renderer_type = None

        if render_type:
            self._renderer = get_renderer(render_type)

        self._frame_skip_counter = 0

    def get_current_image(self) -> PILImage.Image | None:
        return self.current_frame_pil or self.thumbnail

    async def on_mount(self) -> None:
        if not self._open_video():
            return

        if self.preload_frames:
            self._preload_all_frames()

        self._load_thumbnail()

        if self.autoplay:
            self.play()

    def _open_video(self) -> bool:
        try:
            self.container = av.open(self.path)
            self.stream = self.container.streams.video[0]
            self.stream.thread_type = "AUTO"

            self.video_fps = float(self.stream.average_rate or 0)
            self.frame_count = self.stream.frames or 0
            self.duration = (
                float(self.stream.duration * self.stream.time_base)
                if self.stream.duration
                else 0.0
            )

            fps = self.video_fps if self.target_fps == 0 else self.target_fps
            self.frame_interval = max(1.0 / fps, 0.001)

            self.frames = self.container.decode(self.stream)
            return True
        except Exception:
            return False

    def _preload_all_frames(self) -> None:
        try:
            self.preloaded_frames = [frame.to_image() for frame in self.frames]
            self.frame_count = len(self.preloaded_frames)
        except Exception:
            self.preloaded_frames.clear()

    def _load_thumbnail(self) -> None:
        try:
            if self.preloaded_frames:
                self.thumbnail = self.preloaded_frames[0]
            elif self.frames:
                self.thumbnail = next(self.frames).to_image()

            self.current_frame_pil = self.thumbnail
            self._render_frame()
        except Exception:
            pass

    def play(self) -> None:
        if self.is_playing:
            return

        self.is_playing = True
        self._timer = self.set_interval(self.frame_interval, self._next_frame)

    def pause(self) -> None:
        if not self.is_playing:
            return

        self.is_playing = False
        if self._timer:
            self._timer.stop()
            self._timer = None

    def stop(self) -> None:
        self.pause()
        self.current_frame_index = 0

        if self.thumbnail:
            self.current_frame_pil = self.thumbnail
            self._render_frame()

        if not self.preloaded_frames and self.container:
            self._open_video()

    @property
    def progress(self) -> float:
        if self.preloaded_frames:
            return self.current_frame_index / len(self.preloaded_frames)
        return 0.0

    @property
    def current_time(self) -> float:
        if self.preloaded_frames and self.video_fps:
            return self.current_frame_index / self.video_fps
        return 0.0

    def _next_frame(self) -> None:
        try:
            if self.preloaded_frames:
                self.current_frame_index += 1

                if self.current_frame_index >= len(self.preloaded_frames):
                    if self.loop:
                        self.current_frame_index = 0
                    else:
                        self.pause()
                        self.current_frame_pil = self.thumbnail
                        self._render_frame()
                        return

                self.current_frame_pil = self.preloaded_frames[self.current_frame_index]
                self._render_frame()
                return

            if not self.frames:
                return

            if self.low_latency:
                self._frame_skip_counter += 1
                if self._frame_skip_counter > 2:
                    next(self.frames)
                    self._frame_skip_counter = 0
                    return

            self.current_frame_pil = next(self.frames).to_image()
            self._render_frame()

        except StopIteration:
            if self.loop:
                self._open_video()
                self.current_frame_pil = self.thumbnail

            else:
                self._open_video()
                self.current_frame_pil = self.thumbnail
                self._render_frame()

    def _render_frame(self) -> None:

        image = self.current_frame_pil
        if image is None:
            return

        cr = self.content_region
        if not cr or cr.width <= 0 or cr.height <= 0:
            return

        driver = self.app._driver

        renderer = self._renderer
        if not renderer:
            return

        draw(renderer, driver, cr, image)

    def render(self) -> str:
        cr = self.content_region
        if not cr:
            return ""
        return "\n".join(" " * cr.width for _ in range(cr.height))

    def get_graphics(self) -> list[GraphicsCommand]:
        if self.current_frame_pil is None:
            return []
        return super().get_graphics()

    @on(events.Click)
    def _on_click(self, event: events.Click) -> None:
        if self.is_playing:
            self.pause()
        else:
            self.play()
        event.stop()

    @on(events.Resize)
    def _on_resize(self, event: events.Resize) -> None:
        if self.current_frame_pil:
            self.refresh(repaint=True, layout=True)

    def on_unmount(self) -> None:
        self.pause()

        if self.container:
            try:
                self.container.close()
            except Exception:
                pass

        if hasattr(self.app, "screen") and hasattr(self.app.screen, "_compositor"):
            self.app.screen._compositor.unregister_graphic_region(self)

    def _repaint_graphics(self) -> None:
        if self.current_frame_pil:
            self.refresh(repaint=True)
