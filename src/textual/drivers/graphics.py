from __future__ import annotations

from typing import List
from dataclasses import dataclass

from textual.visual import Visual
from textual.geometry import Region


class GraphicsRenderable:
    pass


@dataclass(slots=True)
class GraphicsCommand:
    x: int
    y: int
    payload: bytes


class GraphicsVisual(Visual):
    def render_graphics(self, region: Region) -> List[GraphicsCommand]:
        return []
