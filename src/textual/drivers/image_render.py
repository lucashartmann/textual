from __future__ import annotations

import base64
from enum import Enum, auto
from io import BytesIO
from typing import Protocol, runtime_checkable

from PIL import Image as PILImage

from textual.geometry import Region
from textual.drivers.graphics import GraphicsCommand
from textual.drivers._sixel import image_to_sixels_responsive


@runtime_checkable
class ImageRenderer(Protocol):
    def render_image(
        self,
        image: PILImage.Image,
        region: Region,
    ) -> str | list[str] | GraphicsCommand | list[GraphicsCommand] | None:
        ...


class RenderType(Enum):
    AUTO = auto()
    SIXEL = auto()
    UNICODE = auto()
    NONE = auto()
    TGP = auto()
    HALFCELL = auto()


class HalfcellRenderer:
    def render_image(self, image: PILImage.Image, region: Region) -> list[str]:
        w = region.width
        h = region.height
        if not w or not h:
            return []

        img = image.resize((w, h * 2), PILImage.Resampling.LANCZOS)
        px = img.load()

        lines: list[str] = []

        for y in range(h):
            yy = y * 2
            row = []
            for x in range(w):
                r1, g1, b1 = px[x, yy][:3]
                r2, g2, b2 = px[x, yy + 1][:3]

                row.append(
                    f"\x1b[38;2;{r1};{g1};{b1}m"
                    f"\x1b[48;2;{r2};{g2};{b2}m▀"
                )

            row.append("\x1b[0m")
            lines.append("".join(row))

        return lines


class UnicodeBlockRenderer:
    BLOCKS = [" ", "░", "▒", "▓", "█"]

    def __init__(self) -> None:
        self._max = len(self.BLOCKS) - 1

    def render_image(self, image: PILImage.Image, region: Region) -> str:
        w = region.width
        h = region.height
        if not w or not h:
            return ""

        img = image.resize((w, h), PILImage.Resampling.NEAREST).convert("L")
        px = img.load()

        lines = []
        for y in range(h):
            row = [
                self.BLOCKS[int(px[x, y] / 255 * self._max)]
                for x in range(w)
            ]
            lines.append("".join(row))
        return "\n".join(lines)


class SixelRenderer:
    def render_image(self, image: PILImage.Image, region: Region) -> GraphicsCommand | None:
        sixel = image_to_sixels_responsive(
            image,
            cell_width=region.width,
            cell_height=region.height,
            px_per_cell_x=10,
            px_per_cell_y=20,
        )
        if not sixel:
            return None

        return GraphicsCommand(
            payload=sixel.encode("ascii"),
            x=region.x,
            y=region.y
        )


class TGPRenderer:
    _id_counter = 0

    def __init__(self) -> None:
        self.image_id: int | None = None

    def render_image(self, image: PILImage.Image, region: Region) -> GraphicsCommand | None:
        w = region.width
        h = region.height
        if not w or not h:
            return None

        if self.image_id is None:
            TGPRenderer._id_counter += 1
            self.image_id = TGPRenderer._id_counter

        img = image.resize((w * 8, h * 16), PILImage.Resampling.LANCZOS)

        buf = BytesIO()
        img.save(buf, format="PNG")
        payload = base64.b64encode(buf.getvalue())

        data = (
            f"\x1b_Gf=100,s={w*8},v={h*16},i={self.image_id};"
            .encode("ascii")
            + payload
            + b"\x1b\\"
        )

        return GraphicsCommand(
            payload=data,
            x=region.x,
            y=region.y
        )


RENDERERS: dict[RenderType, type[ImageRenderer]] = {
    RenderType.SIXEL: SixelRenderer,
    RenderType.UNICODE: UnicodeBlockRenderer,
    RenderType.TGP: TGPRenderer,
    RenderType.HALFCELL: HalfcellRenderer,
}


def detect_terminal_capabilities() -> RenderType:
    import os

    term = os.environ.get("TERM", "").lower()
    term_program = os.environ.get("TERM_PROGRAM", "").lower()

    if any(x in term for x in ("xterm", "mintty", "mlterm", "wezterm")):
        return RenderType.SIXEL

    if term_program in ("wezterm",):
        return RenderType.SIXEL

    return RenderType.HALFCELL


def get_renderer(render_type: RenderType) -> ImageRenderer | None:
    if render_type is RenderType.AUTO:
        render_type = detect_terminal_capabilities()

    cls = RENDERERS.get(render_type)
    if not cls:
        return None

    return cls()


def draw(renderer: ImageRenderer, driver, region: Region, image: PILImage.Image) -> None:
    if not region or region.width <= 0 or region.height <= 0:
        return

    out = renderer.render_image(image, region)
    if not out:
        return

    y = region.y + 1
    x = region.x + 1

    if isinstance(out, GraphicsCommand):
        driver.write_graphics([out])
        return

    if isinstance(out, list) and out and isinstance(out[0], GraphicsCommand):
        driver.write_graphics(out)
        return

    if isinstance(out, str):
        lines = out.splitlines()
        for i, line in enumerate(lines[: region.height]):
            driver.write(f"\x1b[{y + i};{x}H{line}")
        return

    if isinstance(out, list):
        for i, line in enumerate(out[: region.height]):
            driver.write(f"\x1b[{y + i};{x}H{line}")
