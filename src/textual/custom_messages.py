from textual.messages import Update as BaseUpdate
from textual.drivers.graphics import GraphicsCommand
from typing import List

class GraphicsUpdate(BaseUpdate):
    def __init__(self, widget, segments: List = None, graphics: List[GraphicsCommand] = None):
        super().__init__(widget)
        self.segments = segments or []
        self.graphics = graphics or []