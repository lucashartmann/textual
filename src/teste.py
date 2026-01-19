from textual.app import App
from textual.drivers.windows_sixel_driver import WindowsSixelDriver
from PIL import Image as PILImage
from textual.widgets._image import Image
from textual.widgets._video import Video
from textual.containers import HorizontalGroup
from textual.widgets import Static

class Teste(App):
    CSS = """
    Image {
        border: tall yellow;
        width: 50;
        height: 30;
        margin: 2;
        background: red;
    }
        """
    
    def get_driver_class(self):
        return WindowsSixelDriver

    def compose(self):
        with HorizontalGroup():
            yield Image("SpongeBob_SquarePants_personagem.png")
            yield Image("SpongeBob_SquarePants_personagem.png")
            yield Image("SpongeBob_SquarePants_personagem.png")
        
Teste().run()

# print("\x1b[10;200H\x1bPq\"1;1;50;50#0;2;0;0;0...")