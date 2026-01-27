from PIL import Image as PILImage
from textual.drivers.image_render import RenderType, draw, get_renderer
from textual import log
from textual.widgets._graphic import Graphic
import io


class Image(Graphic):

    def __init__(self, image: str | bytes | PILImage.Image, render_type: RenderType = RenderType.AUTO, **kwargs):
        super().__init__(render_type=render_type, **kwargs)
        if image:
            if isinstance(image, PILImage.Image):
                self.image = image
            elif isinstance(image, bytes):
                self.image = PILImage.open(io.BytesIO(image))
            else:
                self.image = PILImage.open(image)
        self.preserve_graphics = True
        self._image_scheduled = False
        self._renderer = None
        self._renderer_type = None
        self._last_image_region = None
        self.can_focus = True

        if render_type:
            self._renderer = get_renderer(render_type)

    def render(self) -> str:
        cr = self.content_region
        if not cr:
            return ""
        return "\n".join(" " * cr.width for _ in range(cr.height))

    def _size_updated(self, region_size, virtual_size, container_size, layout=False):
        self.call_after_refresh(self._send_image)

    # @on(events.Resize)
    # def resize(self):
    #     self.call_after_refresh(self._send_image)

    def on_mount(self) -> None:
        self.call_after_refresh(self._send_image)

    def on_unmount(self) -> None:
        self.image.close()
        if hasattr(self.app, "screen") and hasattr(self.app.screen, "_compositor"):
            self.app.screen._compositor._dirty_regions.add(
                self._last_image_region)

    def _repaint_graphics(self) -> None:
        self.call_after_refresh(self._send_image)

    def _send_image(self) -> None:
        self._image_scheduled = False
        if not self.region or not self.image:
            log("ERRO: region ou image não existe")
            return

        image = self.image
        if image is None:
            return

        cr = self.content_region
        if not cr or cr.width <= 0 or cr.height <= 0:
            return

        compositor = self.app.screen._compositor

        region_changed = (self._last_image_region is not None and
                          self._last_image_region != cr)

        viewport_top = self.app.screen.scroll_offset.y
        viewport_bottom = viewport_top + self.app.screen.size.height
        widget_top = self.virtual_region.y
        widget_bottom = widget_top + self.virtual_region.height

        is_visible = not (
            widget_bottom <= viewport_top or widget_top >= viewport_bottom)

        if region_changed or not is_visible:
            compositor._dirty_regions.add(self._last_image_region)

        driver = self.app._driver
        renderer = self._renderer
        if not renderer:
            return

        if is_visible:
            draw(renderer, driver, cr, image)
            self._last_image_region = cr
