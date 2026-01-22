from textual.drivers.graphics import GraphicsCommand
from textual.drivers.image_render import get_renderer, RenderType
from textual.widget import Widget
from textual import log


class Graphic(Widget):

    preserve_graphics = True

    def __init__(
        self,
        render_type: RenderType = RenderType.AUTO,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.render_type = render_type
        self._renderer = None
        self._last_render_type = None

    def get_renderer(self):
        if self._renderer is None or self._last_render_type != self.render_type:
            self._renderer = get_renderer(self.render_type)
            self._last_render_type = self.render_type

            if self._renderer is None:
                log(
                    f"Nenhum renderizador disponível para {self.render_type}")
            else:
                log(f"Usando renderizador: {type(self._renderer).__name__}")

        return self._renderer

    def get_current_image(self):
        raise NotImplementedError(
            "Subclasses devem implementar get_current_image()")

    def render(self) -> str:
        renderer = self.get_renderer()

        if renderer is None:
            return ""

        cr = self.content_region
        if not cr or cr.width <= 0 or cr.height <= 0:
            return ""

        image = self.get_current_image()
        if image is None:
            return ""

        try:
            result = renderer.render_image(image, cr)

            if isinstance(result, str):
                return result

            if isinstance(result, list):
                return "\n".join(" " * cr.width for _ in range(cr.height))

        except Exception as e:
            log(f"Erro ao renderizar: {e}")

        return ""

    def get_graphics(self) -> list[GraphicsCommand]:
        renderer = self.get_renderer()
        if not renderer:
            return []

        cr = self.content_region
        if not cr or cr.width <= 0 or cr.height <= 0:
            return []

        image = self.get_current_image()
        if image is None:
            return []

        try:
            result = renderer.render_image(image, cr)

            if isinstance(result, list):
                for cmd in result:
                    cmd.x = cr.x
                    cmd.y = cr.y
                return result
        except Exception as e:
            log(f"Erro ao gerar graphics: {e}")

        return []

    def on_resize(self) -> None:
        self.refresh(repaint=True, layout=True)

    def on_mount(self) -> None:
        self.refresh()

    def _repaint_graphics(self) -> None:
        self.refresh(repaint=True)
