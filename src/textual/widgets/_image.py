from PIL import Image as PILImage
from textual.widget import Widget
from textual.drivers.graphics import GraphicsCommand
from textual.drivers._sixel import image_to_sixels_responsive
from textual import events, log, on


class Image(Widget):

    def __init__(self, image_path_or_pil=None, **kwargs):
        super().__init__(**kwargs)
        if image_path_or_pil:
            if isinstance(image_path_or_pil, PILImage.Image):
                self.pil_image = image_path_or_pil
            else:
                self.pil_image = PILImage.open(image_path_or_pil)
        self.preserve_graphics = True
        self._sixel_scheduled = False

    def render(self) -> str:
        cr = self.content_region
        if not cr:
            return ""
        return "\n".join(" " * cr.width for _ in range(cr.height))

    def on_mount(self) -> None:
        self._schedule_sixel_redraw()

    def on_unmount(self) -> None:
        self.app.screen._compositor.unregister_graphic_region(self)

    def _repaint_graphics(self) -> None:
        log("_repaint_graphics chamado")
        self._schedule_sixel_redraw()

    def _schedule_sixel_redraw(self) -> None:
        if self._sixel_scheduled:
            return
        self._sixel_scheduled = True
        self.call_after_refresh(self._send_sixel)

    @on(events.Resize)
    def _on_resize(self, event: events.Resize) -> None:
        self._schedule_sixel_redraw()

    def _send_sixel(self) -> None:
        self._sixel_scheduled = False
        if not self.region or not self.pil_image:
            log("ERRO: region ou pil_image não existe")
            return

        cr = self.content_region

        log(f"Content region: x={cr.x}, y={cr.y}, width={cr.width}, height={cr.height}")

        sixel = image_to_sixels_responsive(
            self.pil_image,
            cell_width=cr.width,
            cell_height=cr.height,
            px_per_cell_x=10,
            px_per_cell_y=20,
        )

        if not sixel:
            log("ERRO: sixel está vazio")
            return

        log(f"Sixel gerado com sucesso, tamanho: {len(sixel)}")

        cmd = GraphicsCommand(
            x=cr.x,
            y=cr.y,
            payload=sixel.encode("ascii"),
        )

        log(f"Chamando write_graphics com x={cr.x}, y={cr.y}")
        self.app._driver.write_graphics([cmd])
        self.app.screen._compositor.register_graphic_region(self, cr)
        log("write_graphics chamado com sucesso")

    def get_graphics(self) -> list[GraphicsCommand]:
        if not hasattr(self, 'pil_image') or not self.pil_image:
            return []

        cr = self.content_region

        sixel = image_to_sixels_responsive(
            self.pil_image,
            cell_width=cr.width,
            cell_height=cr.height,
            px_per_cell_x=10,
            px_per_cell_y=20,
        )

        if not sixel:
            return []

        return [
            GraphicsCommand(
                x=cr.x,
                y=cr.y,
                payload=sixel.encode("ascii"),
            )
        ]
