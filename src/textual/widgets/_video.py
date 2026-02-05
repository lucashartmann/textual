from __future__ import annotations
from collections import deque
import av
import time
import numpy as np
import threading
from queue import Queue, Empty
from PIL import Image as PILImage
from textual import events, on
from textual.drivers.graphics import GraphicsCommand
from textual.drivers.image_render import RenderType, get_renderer, draw
from textual.widgets._graphic import Graphic
from textual.binding import Binding, BindingType
from typing import ClassVar

try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    sd = None


class AudioPlayer:

    def __init__(self, audio_stream, speed):
        self.audio_stream = audio_stream
        self.speed = speed
        self.is_playing = False
        self.audio_queue = Queue(maxsize=20)
        self.stream = None
        self.thread = None
        self._stop_event = threading.Event()

        self.sample_rate = int(audio_stream.rate)
        self.channels = audio_stream.channels

        self._leftover = np.array(
            [], dtype=np.float32).reshape(0, self.channels)

        self._start_time = None
        self._samples_played = 0

        self._last_sync_check = 0

    def start(self, start_time=None):
        if not AUDIO_AVAILABLE:
            return

        self.is_playing = True
        self._stop_event.clear()
        self._start_time = start_time or time.time()
        self._samples_played = 0

        self.thread = threading.Thread(target=self._decode_audio, daemon=True)
        self.thread.start()

        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self._audio_callback,
            blocksize=2048
        )
        self.stream.start()

    def stop(self):
        self.is_playing = False
        self._stop_event.set()

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except Empty:
                break

        self._leftover = np.array(
            [], dtype=np.float32).reshape(0, self.channels)

    def set_speed(self, speed: float):
        self.speed = speed

    def _simple_resample(self, audio_data: np.ndarray) -> np.ndarray:
        original_length = len(audio_data)

        new_length = int(original_length / self.speed)

        indices = np.linspace(0, original_length - 1, new_length)

        resampled = np.zeros((new_length, self.channels), dtype=np.float32)
        for ch in range(self.channels):
            resampled[:, ch] = np.interp(indices, np.arange(
                original_length), audio_data[:, ch])

        return resampled

    def _decode_audio(self):
        try:
            for frame in self.audio_stream.container.decode(self.audio_stream):
                if self._stop_event.is_set():
                    break

                audio_data = frame.to_ndarray()

                if audio_data.ndim == 1:
                    audio_data = audio_data.reshape(-1, 1)
                elif audio_data.shape[0] < audio_data.shape[1]:
                    audio_data = audio_data.T

                if audio_data.dtype == np.int16:
                    audio_data = audio_data.astype(np.float32) / 32768.0
                elif audio_data.dtype == np.int32:
                    audio_data = audio_data.astype(np.float32) / 2147483648.0
                else:
                    audio_data = audio_data.astype(np.float32)

                resampled = self._simple_resample(audio_data)

                try:
                    self.audio_queue.put(resampled, timeout=1.0)
                except:
                    if self._stop_event.is_set():
                        break
        except Exception as e:
            pass

    def _audio_callback(self, outdata, frames, time_info, status):
        try:

            needed = frames
            chunks = []
            total_frames = 0

            if len(self._leftover) > 0:
                if len(self._leftover) >= needed:
                    outdata[:] = self._leftover[:needed]
                    self._leftover = self._leftover[needed:]
                    self._samples_played += needed
                    return
                else:
                    chunks.append(self._leftover)
                    total_frames += len(self._leftover)
                    needed -= len(self._leftover)
                    self._leftover = np.array(
                        [], dtype=np.float32).reshape(0, self.channels)

            while needed > 0:
                try:
                    chunk = self.audio_queue.get_nowait()

                    if len(chunk) <= needed:
                        chunks.append(chunk)
                        total_frames += len(chunk)
                        needed -= len(chunk)
                    else:
                        chunks.append(chunk[:needed])
                        self._leftover = chunk[needed:]
                        total_frames += needed
                        needed = 0

                except Empty:
                    break

            if chunks:
                combined = np.vstack(chunks)
                outdata[:len(combined)] = combined
                self._samples_played += len(combined)

                if len(combined) < frames:
                    outdata[len(combined):] = 0
                    self._samples_played += (frames - len(combined))
            else:
                outdata[:] = 0
                self._samples_played += frames

        except Exception as e:
            outdata[:] = 0
            self._samples_played += frames


class Video(Graphic):

    preserve_graphics = True
    contador = 0

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("right", "more_audio_speed", "+ audio_speed"),
        Binding("left", "less_audio_speed", "- audio_speed"),
        Binding("up", "more_video_speed", "+ video_speed"),
        Binding("down", "less_video_speed", "- video_speed"),
        Binding("z", "more_fps", "+ fps"),
        Binding("x", "less_fps", "- fps"),
        Binding("c", "loop", "loop"),
        Binding("v", "render_type", "render_type"),
    ]

    def action_more_audio_speed(self):
        self.audio_speed += 0.1
        self.audio_player.set_speed(self.audio_speed)

    def action_less_audio_speed(self):
        self.audio_speed -= 0.1
        self.audio_player.set_speed(self.audio_speed)

    def action_more_video_speed(self):
        self.speed += 0.1

    def action_less_video_speed(self):
        self.speed -= 0.1

    def action_more_fps(self):
        self.target_fps += 0.1

    def action_less_fps(self):
        self.target_fps -= 0.1

    def action_loop(self):
        if self.loop:
            self.loop = False
        else:
            self.loop = True
        self.call_after_refresh(self._render_frame)

    def action_render_type(self):
        render_type = RenderType._member_names_[self.contador]

        self._renderer = get_renderer(RenderType._member_map_[render_type])
        self.contador += 1
        if self.contador > 5:
            self.contador = 0
        self.call_after_refresh(self._render_frame)

    def __init__(
        self,
        path: str,
        render_type: RenderType = RenderType.AUTO,
        fps: int = 60,
        loop: bool = False,
        autoplay: bool = False,
        low_latency: bool = False,
        preload_frames: bool = False,
        speed: float = 1.0,
        cache_size: int = 0,
        enable_audio: bool = True,
        audio_speed: float = 1.0,
        **kwargs,
    ):
        super().__init__(render_type=render_type, **kwargs)

        self.speed = speed
        # if self.speed == 1.0 and preload_frames == False:
        #     self.speed = 9
        # elif self.speed == 1.0 and preload_frames == True:
        #     self.speed = 1.5
        self.can_focus = True
        self.path = path
        self.target_fps = fps
        self.loop = loop
        self.autoplay = autoplay
        self.low_latency = low_latency
        self.preload_frames = preload_frames
        self.enable_audio = enable_audio and AUDIO_AVAILABLE
        self.audio_speed = audio_speed
        self.container = None
        self.audio_container = None
        self.stream = None
        self.audio_stream = None

        self.frames = None
        self.preloaded_frames: list[PILImage.Image] = []
        self.current_frame_index = 0
        self.current_frame_pil: PILImage.Image | None = None
        self.thumbnail: PILImage.Image | None = None
        self.is_playing = False
        self.video_fps = 0.0
        self.frame_count = 0
        self.duration = 0.0
        self.frame_interval = 1.0 / fps if fps > 0 else 0.001
        self._timer = None
        self._renderer = None
        self._renderer_type = None
        self._last_video_region = None
        self.cache_size = cache_size

        self._start_time = 0.0
        self._pause_time = 0.0
        self._accumulated_pause_time = 0.0

        self.frame_cache: deque = deque(
            maxlen=cache_size if cache_size > 0 else None)
        self.cache_start_index = 0

        if render_type:
            self._renderer = get_renderer(render_type)

        self._frame_skip_counter = 0
        self._streaming_frame_index = 0

        self.audio_player: AudioPlayer | None = None

    def get_current_image(self) -> PILImage.Image | None:
        return self.current_frame_pil or self.thumbnail

    async def on_mount(self) -> None:
        if not self._open_video():
            return

        if self.preload_frames:
            if self.cache_size == 0:
                self._preload_all_frames()
            else:
                self.preloaded_frames = deque(
                    maxlen=self.cache_size if self.cache_size > 0 else None)
                self._init_frame_cache()

        self._load_thumbnail()

        if self.autoplay:
            self.play()

    def _init_frame_cache(self) -> None:
        try:
            for i, frame in enumerate(self.frames):
                if i >= self.cache_size:
                    break
                self.preloaded_frames.append(frame.to_image())
            self.cache_start_index = 0
        except Exception:
            self.preloaded_frames.clear()

    def _open_video(self) -> bool:
        try:
            self.container = av.open(self.path)
            self.stream = self.container.streams.video[0]
            self.stream.thread_type = "AUTO"

            self.video_fps = float(self.stream.average_rate or 0)
            self.frame_count = self.stream.frames or 0
            self.duration = (
                float(self.stream.duration * self.stream.time_base)
                if self.stream.duration
                else 0.0
            )

            fps = self.video_fps if self.target_fps == 0 else self.target_fps
            self.frame_interval = max(1.0 / fps, 0.001)

            self.frames = self.container.decode(self.stream)

            if self.enable_audio:
                try:
                    self.audio_container = av.open(self.path)
                    if len(self.audio_container.streams.audio) > 0:
                        self.audio_stream = self.audio_container.streams.audio[0]
                except Exception:
                    self.enable_audio = False

            return True
        except Exception:
            return False

    def _preload_all_frames(self) -> None:
        try:
            self.preloaded_frames = [frame.to_image() for frame in self.frames]
            self.frame_count = len(self.preloaded_frames)
        except Exception:
            self.preloaded_frames.clear()

    def _load_thumbnail(self) -> None:
        try:
            if self.preloaded_frames:
                self.thumbnail = self.preloaded_frames[0]
            elif self.frames:
                self.thumbnail = next(self.frames).to_image()

            self.current_frame_pil = self.thumbnail
            self._render_frame()
        except Exception:
            pass

    def play(self) -> None:
        if self.is_playing:
            return

        self.is_playing = True

        if self._start_time == 0.0:
            self._start_time = time.time()
        else:
            self._accumulated_pause_time += time.time() - self._pause_time

        if self.enable_audio and self.audio_stream:
            if not self.audio_player:
                self.audio_player = AudioPlayer(
                    self.audio_stream, self.audio_speed)

            self.audio_player.start(
                start_time=self._start_time + self._accumulated_pause_time)

        if self.preloaded_frames:
            self._timer = self.set_interval(
                0.001, self._update_frame_by_timestamp)
        else:
            interval = self.frame_interval / self.speed
            self._timer = self.set_interval(
                interval, self._update_frame_by_timestamp)

    def pause(self) -> None:
        if not self.is_playing:
            return

        self.is_playing = False
        self._pause_time = time.time()

        if self.audio_player:
            self.audio_player.stop()

        if self._timer:
            self._timer.stop()
            self._timer = None

    def stop(self) -> None:
        self.pause()
        self.current_frame_index = 0
        self._streaming_frame_index = 0
        self._start_time = 0.0
        self._pause_time = 0.0
        self._accumulated_pause_time = 0.0

        if self.thumbnail:
            self.current_frame_pil = self.thumbnail
            self._render_frame()

        if not self.preloaded_frames and self.container:
            self._open_video()

    def set_audio_speed(self, speed: float):
        if self.audio_player:
            self.audio_player.set_speed(speed)

    def set_speed(self, speed: float) -> None:
        if speed <= 0:
            speed = 1.0

        old_speed = self.speed

        if self.preloaded_frames:
            if self.is_playing and self._start_time > 0:
                elapsed = time.time() - self._start_time - self._accumulated_pause_time
                current_video_time = elapsed * self.speed
                self.speed = speed
                new_elapsed = current_video_time / self.speed
                self._start_time = time.time() - new_elapsed - self._accumulated_pause_time
            else:
                self.speed = speed
        else:
            was_playing = self.is_playing
            self.speed = speed

            if was_playing and self._timer:
                self._timer.stop()
                self._timer = None
                interval = self.frame_interval / self.speed
                self._timer = self.set_interval(
                    interval, self._update_frame_by_timestamp)

    def _update_frame_by_timestamp(self) -> None:
        if self.preloaded_frames:
            elapsed = time.time() - self._start_time - self._accumulated_pause_time
            video_time = elapsed * self.speed
            target_frame = int(video_time * self.video_fps)

            if target_frame >= len(self.preloaded_frames):
                if self.loop:
                    self._start_time = time.time()
                    self._accumulated_pause_time = 0.0
                    target_frame = 0
                    if self.audio_player:
                        self.audio_player.stop()
                        self._open_video()
                        if self.audio_stream:
                            self.audio_player = AudioPlayer(
                                self.audio_stream, self.audio_speed)
                            self.audio_player.start()
                else:
                    self.pause()
                    return

            if target_frame != self.current_frame_index:
                self.current_frame_index = target_frame
                self.current_frame_pil = self.preloaded_frames[self.current_frame_index]
                self._render_frame()
        else:
            self._next_frame_streaming()

    def _next_frame_streaming(self) -> None:
        try:
            if not self.frames:
                if not self._open_video():
                    return

            frames_to_skip = 0
            if self.speed > 1.0:
                frames_to_skip = int(self.speed) - 1

            for _ in range(frames_to_skip):
                try:
                    next(self.frames)
                    self._streaming_frame_index += 1
                except StopIteration:
                    if self.loop:
                        if self._open_video():
                            self._streaming_frame_index = 0
                            self.current_frame_index = 0
                            if self.audio_player:
                                self.audio_player.stop()
                                if self.audio_stream:
                                    self.audio_player = AudioPlayer(
                                        self.audio_stream, self.audio_speed)
                                    self.audio_player.start()
                        else:
                            self.pause()
                    else:
                        self.pause()
                    return

            frame_data = next(self.frames)
            self.current_frame_pil = frame_data.to_image()
            self._streaming_frame_index += 1
            self.current_frame_index = self._streaming_frame_index
            self._render_frame()

        except StopIteration:
            if self.loop:
                if self._open_video():
                    self._streaming_frame_index = 0
                    self.current_frame_index = 0
                    if self.audio_player:
                        self.audio_player.stop()
                        if self.audio_stream:
                            self.audio_player = AudioPlayer(
                                self.audio_stream, self.audio_speed)
                            self.audio_player.start()
                else:
                    self.pause()
            else:
                self.pause()

        except Exception as e:
            self.pause()

    @property
    def progress(self) -> float:
        if self.preloaded_frames:
            return self.current_frame_index / len(self.preloaded_frames)
        elif self.frame_count > 0:
            return self.current_frame_index / self.frame_count
        return 0.0

    @property
    def current_time(self) -> float:
        if self.video_fps:
            return self.current_frame_index / self.video_fps
        return 0.0

    def _repaint_graphics(self) -> None:
        self.call_after_refresh(self._render_frame)

    def _size_updated(self, region_size, virtual_size, container_size, layout=False):
        self.call_after_refresh(self._render_frame)

    def _render_frame(self) -> None:
        image = self.current_frame_pil
        if image is None:
            return

        cr = self.content_region
        if not cr or cr.width <= 0 or cr.height <= 0:
            return

        region_changed = (self._last_video_region is not None and
                          self._last_video_region != cr)

        viewport_top = self.app.screen.scroll_offset.y
        viewport_bottom = viewport_top + self.app.screen.size.height
        widget_top = self.virtual_region.y
        widget_bottom = widget_top + self.virtual_region.height
        compositor = self.app.screen._compositor

        is_visible = not (
            widget_bottom <= viewport_top or widget_top >= viewport_bottom)

        if region_changed or not is_visible:
            if self.is_playing:
                self.pause()
            compositor._dirty_regions.add(self._last_video_region)

        driver = self.app._driver

        renderer = self._renderer
        if not renderer:
            return

        if is_visible:
            draw(renderer, driver, cr, image)
            self._last_video_region = cr

    def render(self) -> str:
        cr = self.content_region
        if not cr:
            return ""
        return "\n".join(" " * cr.width for _ in range(cr.height))

    def get_graphics(self) -> list[GraphicsCommand]:
        if self.current_frame_pil is None:
            return []
        return super().get_graphics()

    @on(events.Click)
    def _on_click(self, event: events.Click) -> None:
        if self.is_playing:
            self.pause()
        else:
            self.play()
        event.stop()

    def on_unmount(self) -> None:
        self.pause()

        if self.audio_player:
            self.audio_player.stop()
            self.audio_player = None

        if self.container:
            try:
                self.container.close()
            except Exception:
                pass

        if self.audio_container:
            try:
                self.audio_container.close()
            except Exception:
                pass

        if hasattr(self.app, "screen") and hasattr(self.app.screen, "_compositor"):
            self.app.screen._compositor._dirty_regions.add(
                self._last_video_region)

    def get_playback_info(self) -> dict:
        return {
            "speed": self.speed,
            "frame_interval": self.frame_interval,
            "actual_interval": self.frame_interval / self.speed,
            "video_fps": self.video_fps,
            "target_fps": self.target_fps,
            "is_playing": self.is_playing,
            "current_frame": self.current_frame_index,
            "total_frames": self.frame_count,
            "elapsed_time": time.time() - self._start_time - self._accumulated_pause_time if self._start_time > 0 else 0.0,
        }
