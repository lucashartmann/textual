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
        width: 20%;
        height: 30%;
        border: brown;
    }
 
    """

    def compose(self) -> ComposeResult:
        yield Header()

        # yield Video(
        #     path="bob_esponja.mp4",
        #     autoplay=False,
        #     preload_frames=False,
        #     render_type=RenderType.SIXEL,
        #     speed=6.6,
        #     audio_speed=0.8,
        #     fps=30
        # )

        yield Image(image="SpongeBob_SquarePants_personagem.png", render_type=RenderType.SIXEL)
        yield Image(image="SpongeBob_SquarePants_personagem.png", render_type=RenderType.SIXEL)
        yield Image(image="SpongeBob_SquarePants_personagem.png", render_type=RenderType.SIXEL)

        # yield Static("Teste")

        yield Footer()

    def get_driver_class(self):
        return WindowsSixelDriver


if __name__ == "__main__":
    app = VideoTestApp()
    app.run()
