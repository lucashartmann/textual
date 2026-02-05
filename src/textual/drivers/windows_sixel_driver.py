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
        self._last_graphics_count = 0

    def start_application_mode(self) -> None:
        super().start_application_mode()
        self._disable_autorefresh = True

    def stop_application_mode(self) -> None:
        super().stop_application_mode()

    def write_update(self, update) -> None:
        if update.segments:
            super().write_update(update)

        graphics = []
        for widget in self.app.screen.walk_children(method="depth-first"):
            if hasattr(widget, 'get_graphics'):
                g = widget.get_graphics()
                graphics.extend(g)

        if graphics:
            self.write_graphics(graphics)
            self._last_graphics_count = len(graphics)

    def write_graphics(self, commands: Iterable[GraphicsCommand]) -> None:
        if not commands:
            return

        for command in commands:
            self._write_sixel(command)

    def write(self, text: str) -> None:
        super().write(text)

    def _write_sixel(self, command: GraphicsCommand) -> None:
        payload = command.payload

        if isinstance(payload, bytes):
            payload = payload.decode("latin1", errors="replace")

        rewrite_header = payload.startswith("\x1bP0;0;0q")

        if rewrite_header:
            payload = "\x1bPq" + payload[len("\x1bP0;0;0q"):]

        cursor_move = f"\x1b[{command.y + 1};{command.x + 1}H"
        self.write(cursor_move)

        self.write(payload)
