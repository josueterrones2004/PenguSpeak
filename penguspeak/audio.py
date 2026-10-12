
import asyncio
import io
import os
import time
from xml.sax.saxutils import escape

import aiohttp
import discord
from dotenv import load_dotenv

from penguspeak.state import guild_audio_locks
from penguspeak.voices import VOICES


load_dotenv()


# ============================================================
# CONFIGURACIÓN
# ============================================================

TTS_RATE = "+30%"

AZURE_OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"

AZURE_TIMEOUT = aiohttp.ClientTimeout(
    total=30,
    connect=10,
    sock_read=15,
)


def get_azure_config():
    key = os.getenv("AZURE_SPEECH_KEY", "").strip()
    region = os.getenv("AZURE_SPEECH_REGION", "").strip()

    if not key or not region:
        raise RuntimeError(
            "Faltan AZURE_SPEECH_KEY o "
            "AZURE_SPEECH_REGION en .env"
        )

    return key, region


# ============================================================
# STREAM AZURE SPEECH
# ============================================================

class AzureTTSStream:
    """
    Genera un MP3 completo mediante Azure Speech.

    Mantiene la interfaz utilizada por queue.py:
      - start()
      - cancel()

    La generación comienza inmediatamente para permitir
    el prefetch de mensajes pendientes.
    """

    def __init__(
        self,
        text,
        voice_id,
        started_at=None,
    ):
        voice_data = VOICES.get(voice_id)

        if voice_data is None:
            raise ValueError(
                f"Voz desconocida: {voice_id}"
            )

        if voice_data.get("engine") not in (
            "edge",
            "azure",
        ):
            raise ValueError(
                "Motor de voz no compatible: "
                f"{voice_data.get('engine')}"
            )

        self.text = str(text)
        self.voice_id = voice_id
        self.voice = voice_data["voice"]

        self.started_at = (
            started_at
            if started_at is not None
            else time.perf_counter()
        )

        self.task = None
        self.error = None
        self.audio = None

        self.finished = False
        self.first_audio_at = None
        self.completed_at = None

    def start(self):
        if self.task is None:
            self.task = asyncio.create_task(
                self._generate()
            )

        return self.task

    def _build_ssml(self):
        safe_text = escape(self.text)

        safe_voice = escape(
            self.voice,
            {'"': "&quot;"},
        )

        return (
            '<speak version="1.0" '
            'xmlns="http://www.w3.org/2001/10/synthesis" '
            'xml:lang="es-MX">'
            f'<voice name="{safe_voice}">'
            f'<prosody rate="{TTS_RATE}">'
            f"{safe_text}"
            "</prosody>"
            "</voice>"
            "</speak>"
        )

    async def _generate(self):
        key, region = get_azure_config()

        url = (
            f"https://{region}."
            "tts.speech.microsoft.com/"
            "cognitiveservices/v1"
        )

        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": (
                AZURE_OUTPUT_FORMAT
            ),
            "User-Agent": "PenguSpeak/2.0",
        }

        print(
            "[TTS] Motor: Azure Speech | "
            f"Voz: {self.voice}"
        )

        try:
            async with aiohttp.ClientSession(
                timeout=AZURE_TIMEOUT
            ) as session:

                async with session.post(
                    url,
                    headers=headers,
                    data=self._build_ssml().encode(
                        "utf-8"
                    ),
                ) as response:

                    if response.status != 200:
                        detail = (
                            await response.text()
                        )[:300]

                        raise RuntimeError(
                            f"Azure HTTP {response.status}: "
                            f"{detail}"
                        )

                    chunks = []

                    async for chunk in (
                        response.content.iter_chunked(8192)
                    ):
                        if not chunk:
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
                                "Primer audio Azure: "
                                f"{elapsed:.0f} ms"
                            )

                        chunks.append(chunk)

                    self.audio = b"".join(chunks)

                    if not self.audio:
                        raise RuntimeError(
                            "Azure devolvió audio vacío"
                        )

                    self.completed_at = (
                        time.perf_counter()
                    )

                    elapsed = (
                        self.completed_at
                        - self.started_at
                    ) * 1000

                    print(
                        "[TTS PERF] "
                        "MP3 completo: "
                        f"{elapsed:.0f} ms | "
                        f"{len(self.audio)} bytes"
                    )

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            self.error = exc

            print(
                "[TTS] Error Azure Speech: "
                f"{exc!r}"
            )

        finally:
            self.finished = True

    async def get_audio(self):
        if self.task is None:
            self.start()

        await self.task

        if self.error is not None:
            raise self.error

        if not self.audio:
            raise RuntimeError(
                "No se generó audio para reproducir"
            )

        return self.audio

    def cancel(self):
        if (
            self.task is not None
            and not self.task.done()
        ):
            self.task.cancel()


# ============================================================
# CREAR STREAM
# ============================================================

def create_audio_stream(
    text,
    voice_id,
    started_at=None,
):
    stream = AzureTTSStream(
        text=text,
        voice_id=voice_id,
        started_at=started_at,
    )

    stream.start()

    return stream


# ============================================================
# REPRODUCCIÓN EN DISCORD
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
        source = None
        audio_buffer = None
        started_playback = False

        try:
            # Esperamos el MP3 completo.
            # Si ya se generó mediante prefetch,
            # esta espera será prácticamente nula.
            audio = await stream.get_audio()

            if not voice_client.is_connected():
                print(
                    "[TTS] Reproducción cancelada: "
                    "bot desconectado"
                )
                return

            # BytesIO permite que FFmpeg lea el MP3
            # desde memoria sin crear archivos temporales.
            audio_buffer = io.BytesIO(audio)

            source = discord.FFmpegPCMAudio(
                audio_buffer,
                pipe=True,
                before_options="-f mp3",
                options="-vn",
            )

            def after_playing(error):
                if error is not None:
                    print(
                        "[TTS] Error reproduciendo: "
                        f"{error!r}"
                    )

                try:
                    bot.loop.call_soon_threadsafe(
                        finished.set
                    )
                except RuntimeError:
                    pass

            elapsed = (
                time.perf_counter()
                - stream.started_at
            ) * 1000

            print(
                "[TTS PERF] "
                "Iniciando reproducción Discord: "
                f"{elapsed:.0f} ms"
            )

            voice_client.play(
                source,
                after=after_playing,
            )

            started_playback = True

            await finished.wait()

            print(
                "[TTS] Reproducción finalizada"
            )

        except asyncio.CancelledError:
            stream.cancel()

            if started_playback:
                try:
                    voice_client.stop()
                except Exception:
                    pass

            raise

        except Exception as exc:
            print(
                "[TTS] Error reproduciendo audio: "
                f"{exc!r}"
            )

        finally:
            if source is not None:
                try:
                    source.cleanup()
                except Exception:
                    pass

            if audio_buffer is not None:
                audio_buffer.close()