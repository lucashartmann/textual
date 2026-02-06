from textual.app import App, ComposeResult
from textual.drivers.image_render import RenderType
from textual.drivers.windows_sixel_driver import WindowsSixelDriver
from textual.widgets import Static, Video, Image, Header, Footer
from textual.widgets._playlist_video import PlaylistVideo


class VideoTestApp(App):

    CSS = """
    Screen {
        align: center middle;
    }
    
    # Video {
    #     width: 50%;
    #     height: 90%;
    #     border: brown;
    # }
    
    Image {
        width: 20%;
        height: 30%;
        border: brown;
    }
    
    PlaylistVideo Video {
        width: 100%;
        height: 95%;
    }
    
    PlaylistVideo Container {
        width: 100%;
        height: 100%;
    }
    
    PlaylistVideo {
        width: 90%;
        height: 90%;
        border: brown;
    }
 
    """

    def compose(self) -> ComposeResult:
        yield Header()
        
        # yield PlaylistVideo(
        #     playlist_path="br.m3u",
        #     render_type=RenderType.SIXEL,
        #     autoplay=True,
        #     fps=30,
        #     enable_audio=True,
        # )

        # yield Video(
        #     path="bob_esponja.mp4",
        #     autoplay=False,
        #     preload_frames=False,
        #     render_type=RenderType.SIXEL,
        #     speed=6.6,
        #     audio_speed=0.8,
        #     fps=30
        # )

        # yield Image(image="SpongeBob_SquarePants_personagem.png", render_type=RenderType.SIXEL)
        # yield Image(image="SpongeBob_SquarePants_personagem.png", render_type=RenderType.SIXEL)
        # yield Image(image="SpongeBob_SquarePants_personagem.png", render_type=RenderType.SIXEL)

        # yield Static("Teste")

        yield Footer(show_command_palette=False)

    def get_driver_class(self):
        return WindowsSixelDriver


if __name__ == "__main__":
    app = VideoTestApp()
    app.run()
