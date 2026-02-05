from itertools import groupby
from PIL import Image as PILImage
from typing import Iterable, Iterator, TypeVar

T = TypeVar("T")
DCS = "\x1bP"
ST = "\x1b\\"
COLORS = 256


def grouped(iterable: Iterable[T], n: int) -> Iterator[Iterable[T]]:
    return zip(*([iter(iterable)] * n), strict=True)


def image_to_sixels_responsive(
    image: PILImage.Image,
    cell_width: int,
    cell_height: int,
    px_per_cell_x: int = 9,
    px_per_cell_y: int = 18
) -> str:
    target_w = cell_width * px_per_cell_x
    target_h = cell_height * px_per_cell_y

    img = image.resize((target_w, target_h), PILImage.Resampling.LANCZOS)
    w, h = img.size

    img = img.convert("P", palette=PILImage.Palette.ADAPTIVE, colors=COLORS)

    sixel_mode = f"{DCS}0;0;0"
    raster_attributes = f'q"1;1;{w};{h}'

    color_registers = []
    palette = img.getpalette() or []
    for i, color in enumerate(grouped(palette, 3)):
        if i >= COLORS:
            break
        color_str = ";".join(str(int(channel / 256 * 100))
                             for channel in color)
        color_registers.append(f"#{i};2;{color_str}")

    header = f"{sixel_mode}{raster_attributes}{''.join(color_registers)}"

    tokens = []
    for y, row in enumerate(grouped(img.getdata(), w)):
        n = 1 << (y % 6)

        for color, group in groupby(row):
            tokens.append(f"#{color}")
            count = len(list(group))
            if count < 3:
                tokens.append(chr(0x3F + n) * count)
            else:
                tokens.append(f"!{count}{chr(0x3F + n)}")
        tokens.append("-" if n == 32 else "$")

    return header + "".join(tokens) + ST
