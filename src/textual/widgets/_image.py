from PIL import Image as PILImage
from textual.drivers.image_render import RenderType, draw, get_renderer
from textual import events, log, on
from textual.geometry import Size
from textual.widgets._graphic import Graphic
import io

class Image(Graphic):

    PRESERVE_ON_RESIZE = True

    def __init__(self, image:str|bytes|PILImage.Image, render_type: RenderType = RenderType.AUTO, **kwargs):
        super().__init__(render_type=render_type, **kwargs)
        if image:
            if isinstance(image, PILImage.Image):
                self.image = image
            elif isinstance(image, bytes):
                self.image = PILImage.open(io.BytesIO(image))
            else:
                self.image = PILImage.open(image)
        self.preserve_graphics = True
        self._sixel_scheduled = False
        self._renderer = None
        self._renderer_type = None

        if render_type:
            self._renderer = get_renderer(render_type)
            
    def _size_updated(
        self, size: Size, virtual_size: Size, container_size: Size, layout: bool = False
    ) -> bool:
        
                
        compositor = self.screen._compositor
        log(f"_size_updated region {self.region}")
        if hasattr(compositor, '_dirty_regions') and self.region:
                log(f"compositor._dirty_regions.discard(self.region)")
                compositor._dirty_regions.discard(self.region)
                compositor._dirty_regions.discard(self.content_region)

    def render(self) -> str:
        cr = self.content_region
        if not cr:
            return ""
        return "\n".join(" " * cr.width for _ in range(cr.height))
    

    def on_mount(self) -> None:
        self._schedule_sixel_redraw()

    def on_unmount(self) -> None:
        self.image.close()
        self.app.screen._compositor.unregister_graphic_region(self)

    def _repaint_graphics(self) -> None:
        self._schedule_sixel_redraw()

    def _schedule_sixel_redraw(self) -> None:
        if self._sixel_scheduled:
            return
        self._sixel_scheduled = True
        self.call_after_refresh(self._send_sixel)


    def _send_sixel(self) -> None:
        self._sixel_scheduled = False
        if not self.region or not self.image:
            log("ERRO: region ou image não existe")
            return
        
        image = self.image
        if image is None:
            return

        cr = self.content_region
        if not cr or cr.width <= 0 or cr.height <= 0:
            return

        driver = self.app._driver

        renderer = self._renderer
        if not renderer:
            return

        draw(renderer, driver, cr, image)
        self.app.screen._compositor.register_graphic_region(self, cr)
