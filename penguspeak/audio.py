import asyncio
import subprocess
import time

import discord
import edge_tts

from penguspeak.state import guild_audio_locks
from penguspeak.voices import VOICES


# ============================================================
# CONFIGURACIÓN LOW LATENCY
# ============================================================

TTS_RATE = "+30%"

# Cantidad máxima de fragmentos MP3 preparados en RAM.
STREAM_BUFFER_SIZE = 32

# Discord usa PCM:
# 48 kHz × 2 canales × 2 bytes × 20 ms = 3840 bytes.
DISCORD_PCM_FRAME_SIZE = 3840


# ============================================================
# STREAM EDGE TTS
# ============================================================

class EdgeTTSStream:
    """
    Recibe audio desde Edge TTS progresivamente.

    No espera a que Edge termine de generar todo el mensaje.
    """

    def __init__(
        self,
        text,
        voice_id,
        started_at=None,
    ):
        data = VOICES.get(
            voice_id
        )

        if not data:
            raise ValueError(
                f"Voz desconocida: {voice_id}"
            )

        if data["engine"] != "edge":
            raise ValueError(
                f"Motor no compatible: {data['engine']}"
            )

        self.text = text
        self.voice_id = voice_id
        self.voice = data["voice"]

        self.started_at = (
            started_at
            if started_at is not None
            else time.perf_counter()
        )

        self.loop = asyncio.get_running_loop()

        self.queue = asyncio.Queue(
            maxsize=STREAM_BUFFER_SIZE
        )

        self.task = None

        self.error = None
        self.finished = False
        self.first_audio_at = None

    def start(
        self,
    ):
        if (
            self.task is None
            or self.task.done()
        ):
            self.task = asyncio.create_task(
                self._producer()
            )

        return self.task

    async def _producer(
        self,
    ):
        cancelled = False

        communicate = edge_tts.Communicate(
            self.text,
            self.voice,
            rate=TTS_RATE,
        )

        try:
            async for chunk in communicate.stream():
                if chunk["type"] != "audio":
                    continue

                if self.first_audio_at is None:
                    self.first_audio_at = (
                        time.perf_counter()
                    )

                    elapsed = (
                        self.first_audio_at
                        - self.started_at
                    ) * 1000

                    print(
                        "[TTS PERF] "
                        "Primer audio Edge: "
                        f"{elapsed:.0f} ms"
                    )

                await self.queue.put(
                    chunk["data"]
                )

        except asyncio.CancelledError:
            cancelled = True
            raise

        except Exception as exc:
            self.error = exc

            print(
                "[TTS] Error Edge TTS: "
                f"{exc!r}"
            )

        finally:
            self.finished = True

            # En finalización normal avisamos al consumidor
            # de que no habrá más audio.
            if not cancelled:
                try:
                    await self.queue.put(
                        None
                    )

                except asyncio.CancelledError:
                    pass

    async def get_chunk(
        self,
    ):
        return await self.queue.get()

    def cancel(
        self,
    ):
        """
        Puede llamarse desde asyncio o desde el hilo
        de reproducción de discord.py.
        """

        if (
            self.task is None
            or self.task.done()
        ):
            return

        try:
            self.loop.call_soon_threadsafe(
                self.task.cancel
            )

        except RuntimeError:
            pass


# ============================================================
# AUDIO SOURCE DE DISCORD
# ============================================================

class EdgeStreamingAudioSource(
    discord.AudioSource
):
    """
    Flujo:

        Edge MP3
            ↓
        FFmpeg
            ↓
        PCM 48 kHz estéreo
            ↓
        Discord

    La escritura a FFmpeg nunca bloquea el event loop.
    """

    def __init__(
        self,
        stream,
    ):
        self.stream = stream

        self.loop = asyncio.get_running_loop()

        self.first_pcm_at = None
        self.closed = False

        command = [
            "ffmpeg",

            "-hide_banner",
            "-loglevel",
            "error",

            # Reducir buffering inicial.
            "-fflags",
            "nobuffer",

            "-probesize",
            "32",

            "-analyzeduration",
            "0",

            # Edge entrega MP3.
            "-f",
            "mp3",

            "-i",
            "pipe:0",

            # Salida PCM requerida por discord.py.
            "-f",
            "s16le",

            "-ar",
            "48000",

            "-ac",
            "2",

            "pipe:1",
        ]

        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )

        self.writer_task = asyncio.create_task(
            self._feed_ffmpeg()
        )

    # ========================================================
    # EDGE -> FFMPEG
    # ========================================================

    def _write_chunk_blocking(
        self,
        data,
    ):
        """
        Escritura bloqueante ejecutada mediante to_thread().
        """

        stdin = self.process.stdin

        if (
            stdin is None
            or stdin.closed
            or self.process.poll() is not None
        ):
            return False

        try:
            view = memoryview(
                data
            )

            while view:
                if (
                    self.closed
                    or self.process.poll() is not None
                ):
                    return False

                written = stdin.write(
                    view
                )

                if written is None:
                    continue

                if written <= 0:
                    return False

                view = view[
                    written:
                ]

            return True

        except (
            BrokenPipeError,
            ValueError,
            OSError,
        ):
            return False

    async def _feed_ffmpeg(
        self,
    ):
        try:
            while True:
                data = await self.stream.get_chunk()

                if data is None:
                    break

                if (
                    self.closed
                    or self.process.stdin is None
                    or self.process.poll() is not None
                ):
                    break

                success = await asyncio.to_thread(
                    self._write_chunk_blocking,
                    data,
                )

                if not success:
                    break

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            print(
                "[TTS] Error enviando "
                f"audio a FFmpeg: {exc!r}"
            )

        finally:
            try:
                if (
                    self.process.stdin
                    and not self.process.stdin.closed
                ):
                    self.process.stdin.close()

            except Exception:
                pass

    # ========================================================
    # FFMPEG -> DISCORD
    # ========================================================

    def read(
        self,
    ):
        """
        Discord llama a read() desde su propio hilo.

        Debemos devolver exactamente 3840 bytes por frame,
        salvo cuando el audio haya terminado realmente.
        """

        if (
            self.closed
            or self.process.stdout is None
        ):
            return b""

        frame = bytearray()

        try:
            while (
                len(frame)
                < DISCORD_PCM_FRAME_SIZE
            ):
                remaining = (
                    DISCORD_PCM_FRAME_SIZE
                    - len(frame)
                )

                chunk = self.process.stdout.read(
                    remaining
                )

                # EOF real de FFmpeg.
                if not chunk:
                    break

                frame.extend(
                    chunk
                )

        except (
            ValueError,
            OSError,
        ):
            return b""

        # No llegó absolutamente nada:
        # el audio terminó.
        if not frame:
            return b""

        if self.first_pcm_at is None:
            self.first_pcm_at = (
                time.perf_counter()
            )

            elapsed = (
                self.first_pcm_at
                - self.stream.started_at
            ) * 1000

            print(
                "[TTS PERF] "
                "Primer PCM para Discord: "
                f"{elapsed:.0f} ms"
            )

        # Si el último frame queda incompleto,
        # rellenamos el resto con silencio.
        if (
            len(frame)
            < DISCORD_PCM_FRAME_SIZE
        ):
            frame.extend(
                b"\x00"
                * (
                    DISCORD_PCM_FRAME_SIZE
                    - len(frame)
                )
            )

        return bytes(
            frame
        )

    def is_opus(
        self,
    ):
        return False

    # ========================================================
    # LIMPIEZA
    # ========================================================

    def cleanup(
        self,
    ):
        """
        Puede ejecutarse desde el hilo de audio de Discord.
        """

        if self.closed:
            return

        self.closed = True

        self.stream.cancel()

        if (
            self.writer_task
            and not self.writer_task.done()
        ):
            try:
                self.loop.call_soon_threadsafe(
                    self.writer_task.cancel
                )

            except RuntimeError:
                pass

        # Matar FFmpeg desbloquea cualquier write/read pendiente.
        try:
            if self.process.poll() is None:
                self.process.kill()

        except Exception:
            pass

        try:
            if (
                self.process.stdin
                and not self.process.stdin.closed
            ):
                self.process.stdin.close()

        except Exception:
            pass

        try:
            if (
                self.process.stdout
                and not self.process.stdout.closed
            ):
                self.process.stdout.close()

        except Exception:
            pass

        try:
            self.process.wait(
                timeout=0.5
            )

        except Exception:
            pass


# ============================================================
# CREAR STREAM
# ============================================================

def create_audio_stream(
    text,
    voice_id,
    started_at=None,
):
    stream = EdgeTTSStream(
        text=text,
        voice_id=voice_id,
        started_at=started_at,
    )

    stream.start()

    return stream


# ============================================================
# REPRODUCIR
# ============================================================

async def play_audio(
    bot,
    guild_id,
    voice_client,
    stream,
):
    lock = guild_audio_locks.setdefault(
        guild_id,
        asyncio.Lock(),
    )

    async with lock:
        finished = asyncio.Event()

        source = EdgeStreamingAudioSource(
            stream
        )

        def after_playing(
            error,
        ):
            if error:
                print(
                    "[TTS] Error reproduciendo audio: "
                    f"{error!r}"
                )

            bot.loop.call_soon_threadsafe(
                finished.set
            )

        try:
            voice_client.play(
                source,
                after=after_playing,
            )

            await finished.wait()

        finally:
            # Normalmente discord.py ya hace cleanup(),
            # pero esto garantiza que FFmpeg/Edge no queden vivos.
            try:
                source.cleanup()

            except Exception:
                pass