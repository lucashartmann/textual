from textual import events, log
from textual._on import on
from textual.app import App
from textual.drivers.image_render import RenderType
from textual.drivers.windows_sixel_driver import WindowsSixelDriver
from textual.screen import Screen
from textual.widgets._graphic import Graphic
from textual.widgets._video import Video
from textual.widgets._image import Image
from textual.containers import HorizontalGroup
from textual.widgets import Static, Header


class Teste(App):
    CSS = """
    Screen {
        background: gray 30%;
    }
    Video, Image, Static {
        border: tall yellow;
        width: 30;
        height: 15;
        margin: 2;
    }
    Region {
        border: green;
    }
        """

    def get_driver_class(self):
        return WindowsSixelDriver

    def compose(self):

        # yield Video("Sample Videos.mp4", fps=60, render_type=RenderType.SIXEL, autoplay=True)
        # yield Image("SpongeBob_SquarePants_personagem.png")
        # yield Header()
        yield Image("SpongeBob_SquarePants_personagem.png", render_type=RenderType.SIXEL)
        # yield Image("SpongeBob_SquarePants_personagem.png")

        yield Static("test")
        yield Static("test")
        yield Static("test")
        yield Static("test")
        yield Static("test")

    # @on(events.Resize)
    # def _app_on_resize(self, event: events.Resize) -> None:
    #     log(f"App resize → novo tamanho terminal: {event.size}")

    #     if self.screen:

    #         # self.screen.refresh(layout=True, repaint=True)

    #         def delayed_redraw():
    #             for widget in self.query(Graphic):
    #                 log(f"Forçando redraw completo em {widget}")
    #                 if hasattr(widget, '_send_sixel'):
    #                     # widget._last_content_region = None
    #                     widget._send_sixel()

    #         self.call_after_refresh(delayed_redraw)
    #         self.call_later(delayed_redraw)


Teste().run()

# print("\x1b[10;200H\x1bPq\"1;1;50;50#0;2;0;0;0...")
