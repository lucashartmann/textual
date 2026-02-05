from textual.app import App, ComposeResult
from textual.drivers.image_render import RenderType
from textual.drivers.windows_sixel_driver import WindowsSixelDriver
from textual.widgets import Static, Video, Image, Header, Footer


class VideoTestApp(App):

    CSS = """
    Screen {
        align: center middle;
    }
    
    Video {
        width: 50%;
        height: 90%;
        border: brown;
    }
    
    Image {
        width: 50%;
        height: 90%;
        border: brown;
    }
 
    """

    def compose(self) -> ComposeResult:
        yield Header()

        yield Video(
            path="World’s Most Dangerous Escape Room! [3jS_yEK8qVI].mp4",
            autoplay=False,
            preload_frames=False,
            render_type=RenderType.SIXEL,
            speed=4,
            audio_speed=0.8
        )

        # yield Image(image="SpongeBob_SquarePants_personagem.png", render_type=RenderType.SIXEL)

        # yield Static("Teste")

        yield Footer()

    def get_driver_class(self):
        return WindowsSixelDriver


if __name__ == "__main__":
    app = VideoTestApp()
    app.run()
