from __future__ import annotations

from textual import log
import threading
from typing import Iterable

from textual.drivers.windows_driver import WindowsDriver
from textual.drivers.graphics import GraphicsCommand
from textual.geometry import Region


class WindowsSixelDriver(WindowsDriver):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._graphics_already_sent = False  
        self._graphics_lock = threading.Lock()
        self._graphics_region_active: bool = False
        self._graphics_region: Region | None = None
        log("WindowsSixelDriver custom INSTANCIADO com sucesso!")

    def start_application_mode(self) -> None:
        log("WindowsSixelDriver start_application_mode chamado")
        super().start_application_mode()

        self._disable_autorefresh = True

    def stop_application_mode(self) -> None:
        super().stop_application_mode()

    def write_update(self, update) -> None:
        log("WindowsSixelDriver write_update chamado! (deve aparecer sempre que houver update)")

        if update.segments:
            super().write_update(update)

        graphics = []
        log("Coletando graphics...")
        for widget in self.app.screen.walk_children(method="depth-first"):
            if hasattr(widget, 'get_graphics'):
                log(f" - Widget {widget.__class__.__name__} tem get_graphics")
                g = widget.get_graphics()
                log(f"   → retornou {len(g)} comandos")
                graphics.extend(g)

        if graphics:
            log(f"Total: Enviando {len(graphics)} comandos SIXEL")
            self.write_graphics(graphics)
        else:
            log("Nenhum graphics encontrado - problema aqui!")

    def write_graphics(self, commands: Iterable[GraphicsCommand]) -> None:
        log("WindowsSixelDriver write_graphics chamado")
        for command in commands:
            self._write_sixel(command)

    def write(self, text: str) -> None:
        log("WindowsSixelDriver write chamado")
        if self._graphics_region_active:
            return
        super().write(text)

    def _write_sixel(self, command: GraphicsCommand) -> None:
        log(f"WindowsSixelDriver _write_sixel: x={command.x}, y={command.y}")

        cursor_move = f"\x1b[{command.y + 1};{command.x + 1}H"
        self.write("\x1b[?6l")
        self.write(cursor_move)

        payload = command.payload
        rewrite_header = payload.startswith(b"\x1bP0;0;0q")
        if rewrite_header:
            payload = b"\x1bPq" + payload[len(b"\x1bP0;0;0q"):]

        log(f"WindowsSixelDriver SIXEL header rewrite={rewrite_header}")

        payload_text = payload.decode("ascii", errors="strict")
        self.write(payload_text)

        log(f"Sixel enviado diretamente na posição ({command.x}, {command.y})")
