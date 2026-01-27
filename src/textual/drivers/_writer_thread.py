from __future__ import annotations

import threading
from queue import Queue
from typing import TextIO

from typing_extensions import Final

MAX_QUEUED_WRITES: Final[int] = 30


class WriterThread(threading.Thread):
    """A thread / file-like to do writes to stdout in the background."""

    def __init__(self, file: TextIO) -> None:
        super().__init__(daemon=True, name="textual-output")
        self._queue: Queue[str | bytes | None] = Queue(MAX_QUEUED_WRITES)
        self._file = file
        self._graphics_callback = None

    def set_graphics_callback(self, callback) -> None:
        self._graphics_callback = callback

    def write(self, text: str) -> None:
        """Write text. Text will be enqueued for writing.

        Args:
            text: Text to write to the file.
        """
        
        self._queue.put(text)

    def write_bytes(self, data: bytes) -> None:
        """Write raw bytes (e.g. SIXEL)."""
        self._queue.put(data)

    def isatty(self) -> bool:
        """Pretend to be a terminal.

        Returns:
            True.
        """
        return True

    def fileno(self) -> int:
        """Get file handle number.

        Returns:
            File number of proxied file.
        """
        return self._file.fileno()

    def flush(self) -> None:
        """Flush the file (a no-op, because flush is done in the thread)."""
        return

    def run(self):
        write = self._file.write
        write_bytes = self._file.buffer.write
        flush = self._file.flush

        while True:
            item = self._queue.get()
            if item is None:
                break

            if isinstance(item, bytes):
                flush()
                write_bytes(item)
            else:
                write(item)

            if self._queue.empty():
                flush()

                if self._graphics_callback:
                    self._graphics_callback()

        flush()

    def stop(self) -> None:
        """Stop the thread, and block until it finished."""
        self._queue.put(None)
        self.join()
