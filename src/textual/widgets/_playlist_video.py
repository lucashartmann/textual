from textual.drivers.image_render import RenderType
from textual.widget import Widget
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Video
from textual.widgets._static import Static

def parse_m3u(path: str) -> list[str]:
    urls = []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)

    return urls


class PlaylistVideo(Widget):

    BINDINGS = [
        Binding("n", "next", "Next"),
        Binding("p", "prev", "Prev"),
        Binding("space", "play_pause", "Play/Pause"),
    ]

    def __init__(
        self,
        playlist_path: str,
        autoplay: bool = True,
        loop_playlist: bool = True,
        **video_kwargs,
    ):
        super().__init__()

        self.playlist_path = playlist_path
        self.entries: list[str] = parse_m3u(playlist_path)
        self.index = 0
        self.loop_playlist = loop_playlist
        self.autoplay = autoplay
        self.can_focus = True

        self.video = Video(
            path=self.entries[0],
            autoplay=True,
            render_type=RenderType.SIXEL,
        )
        

    def compose(self):
        yield Container(Static(f"Pausado: {self.video.is_playing}"), self.video)

    def action_play_pause(self):
        if self.video.is_playing:
            self.video.pause()
        else:
            self.video.play()
        self.query_one(Static).update(f"Pausado: {not self.video.is_playing}")

    def action_next(self):
        self._change(1)

    def action_prev(self):
        self._change(-1)

    def _change(self, step: int):
        self.video.stop()

        self.index += step

        if self.index >= len(self.entries):
            if self.loop_playlist:
                self.index = 0
            else:
                return

        if self.index < 0:
            if self.loop_playlist:
                self.index = len(self.entries) - 1
            else:
                return

        try:
            self.video.path = self.entries[self.index]
            self.video._open_video()
            # self.video._render_frame()

            if self.autoplay:
                self.video.play()
        except:
            self._change(1)
            
        self.screen.notify("Canal Trocado!")
