import asyncio
import os
import queue
import threading
import time
from xml.sax.saxutils import escape
import aiohttp
import discord
import edge_tts
from dotenv import load_dotenv
from penguspeak.state import guild_audio_locks
from penguspeak.voices import VOICES
load_dotenv()
# ============================================================
# CONFIGURACIÓN
# ============================================================
TTS_RATE = "+30%"
EDGE_TIMEOUT_SECONDS = 20
EDGE_RETRY_SECONDS = 60
AZURE_OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"
AZURE_TIMEOUT = aiohttp.ClientTimeout(
    total=30,
    connect=10,
    sock_read=15,
)
# Objetivo aproximado: 250 ms de audio comprimido.
# Depende del bitrate real del MP3.
INITIAL_BUFFER_BYTES = 1600
# Solo registramos esperas suficientemente largas.
BUFFER_WAIT_WARNING_MS = 100
_active_engine = "edge"
_last_edge_failure = 0.0
_edge_recovery_task = None
_EDGE_PROBE_TEXT = "Prueba de conexión."

_engine_change_callback = None

def set_engine_change_callback(callback):
    """Registra un observador; nunca bloquea la generación TTS."""
    global _engine_change_callback
    _engine_change_callback = callback

def get_active_engine():
    return _active_engine
def get_azure_config():
    key = os.getenv("AZURE_SPEECH_KEY", "").strip()
    region = os.getenv("AZURE_SPEECH_REGION", "").strip()
    if not key or not region:
        return None
    return key, region
def _set_engine(engine):
    global _active_engine
    if _active_engine == engine:
        return
    previous = _active_engine
    _active_engine = engine
    if _engine_change_callback is not None:
        try:
            asyncio.create_task(_engine_change_callback(previous, engine))
        except Exception as exc:
            print(f"[TTS NOTICE] Error programando aviso: {exc!r}")
    print(f"[TTS ENGINE] {previous.upper()} -> {engine.upper()}")
    if engine == "azure":
        print("[TTS ENGINE] Edge no disponible. Usando Azure temporalmente.")
    else:
        print("[TTS ENGINE] Edge se ha restablecido.")
async def _probe_edge():
    """Comprueba Edge sin enviar el audio de prueba a Discord."""
    communicator = edge_tts.Communicate(
        text=_EDGE_PROBE_TEXT,
        voice="es-MX-JorgeNeural",
        rate=TTS_RATE,
    )
    received = False
    async def receive():
        nonlocal received
        async for chunk in communicator.stream():
            if chunk.get("type") == "audio" and chunk.get("data"):
                received = True
    await asyncio.wait_for(receive(), timeout=EDGE_TIMEOUT_SECONDS)
    if not received:
        raise RuntimeError("Edge devolvió audio vacío durante la prueba")
async def _edge_recovery_loop():
    """Prueba Edge cada 60 s mientras Azure está activo."""
    global _last_edge_failure
    try:
        while _active_engine == "azure":
            await asyncio.sleep(EDGE_RETRY_SECONDS)
            if _active_engine != "azure":
                return
            try:
                await _probe_edge()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                _last_edge_failure = time.monotonic()
                print(f"[TTS ENGINE] Edge sigue sin responder: {exc!r}")
            else:
                _set_engine("edge")
                return
    except asyncio.CancelledError:
        raise
def _ensure_recovery_task():
    global _edge_recovery_task
    if _active_engine != "azure":
        return
    if _edge_recovery_task is None or _edge_recovery_task.done():
        _edge_recovery_task = asyncio.create_task(_edge_recovery_loop())
# ============================================================
# BÚFER PROGRESIVO
# ============================================================
class StreamingMP3Buffer:
    """
    Permite que FFmpeg lea MP3 mientras Edge/Azure
    continúa enviando fragmentos.
    Usa una cola segura entre hilos porque discord.py
    lee el pipe fuera del event loop.
    """
    def __init__(self):
        self._queue = queue.Queue()
        self._pending = bytearray()
        self._lock = threading.Lock()
        self._closed = False
        self._eof = False
        self.total_received = 0
        self.total_read = 0
        self.wait_count = 0
        self.total_wait_ms = 0.0
        self.max_wait_ms = 0.0
    def feed(self, data):
        if not data:
            return
        with self._lock:
            if self._closed:
                return
            data = bytes(data)
            self.total_received += len(data)
            self._queue.put(data)
    def finish(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._queue.put(None)
    def read(self, size=-1):
        if size is None or size <= 0:
            size = 8192
        while not self._pending:
            if self._eof:
                return b""
            started = time.perf_counter()
            chunk = self._queue.get()
            waited_ms = (
                time.perf_counter() - started
            ) * 1000
            if waited_ms >= BUFFER_WAIT_WARNING_MS:
                self.wait_count += 1
                self.total_wait_ms += waited_ms
                self.max_wait_ms = max(
                    self.max_wait_ms,
                    waited_ms,
                )
                print(
                    "[TTS BUFFER] FFmpeg esperó "
                    f"{waited_ms:.0f} ms por audio"
                )
            if chunk is None:
                self._eof = True
                return b""
            self._pending.extend(chunk)
        result = bytes(self._pending[:size])
        del self._pending[:size]
        self.total_read += len(result)
        return result
    def close(self):
        self.finish()
    def stats(self):
        return {
            "received": self.total_received,
            "read": self.total_read,
            "waits": self.wait_count,
            "total_wait_ms": self.total_wait_ms,
            "max_wait_ms": self.max_wait_ms,
        }
# ============================================================
# STREAM TTS
# ============================================================
class TTSStream:
    def __init__(self, text, voice_id, started_at=None):
        voice_data = VOICES.get(voice_id)
        if voice_data is None:
            raise ValueError(
                f"Voz desconocida: {voice_id}"
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
        self.engine = None
        self.finished = False
        self.first_audio_at = None
        self.completed_at = None
        self._chunks = []
        self._received_bytes = 0
        self._buffer = StreamingMP3Buffer()
        self._buffer_ready = asyncio.Event()
        self._cancelled = False
    def start(self):
        if self.task is None:
            self.task = asyncio.create_task(
                self._generate()
            )
        return self.task
    def _record_first_audio(self, engine):
        if self.first_audio_at is not None:
            return
        self.first_audio_at = time.perf_counter()
        elapsed = (
            self.first_audio_at - self.started_at
        ) * 1000
        print(
            f"[TTS PERF] Primer fragmento {engine}: "
            f"{elapsed:.0f} ms"
        )
    def _receive_chunk(self, data, engine):
        if not data or self._cancelled:
            return
        self.engine = engine
        self._record_first_audio(engine)
        data = bytes(data)
        self._chunks.append(data)
        self._received_bytes += len(data)
        self._buffer.feed(data)
        if (
            self._received_bytes >= INITIAL_BUFFER_BYTES
            and not self._buffer_ready.is_set()
        ):
            elapsed = (
                time.perf_counter() - self.started_at
            ) * 1000
            print(
                "[TTS BUFFER] Búfer inicial listo: "
                f"{self._received_bytes} bytes | "
                f"{elapsed:.0f} ms"
            )
            self._buffer_ready.set()
    def _record_completion(self):
        self.completed_at = time.perf_counter()
        elapsed = (
            self.completed_at - self.started_at
        ) * 1000
        print(
            "[TTS PERF] MP3 completo: "
            f"{elapsed:.0f} ms | "
            f"{len(self.audio)} bytes | "
            f"Motor: {self.engine}"
        )
    # ========================================================
    # EDGE TTS
    # ========================================================
    async def _generate_edge(self):
        print(
            "[TTS] Generando con Edge TTS | "
            f"Voz: {self.voice}"
        )
        communicate = edge_tts.Communicate(
            text=self.text,
            voice=self.voice,
            rate=TTS_RATE,
        )
        async def receive():
            async for chunk in communicate.stream():
                if chunk.get("type") != "audio":
                    continue
                data = chunk.get("data")
                if data:
                    self._receive_chunk(
                        data,
                        "edge",
                    )
        await asyncio.wait_for(
            receive(),
            timeout=EDGE_TIMEOUT_SECONDS,
        )
        if not self._chunks:
            raise RuntimeError(
                "Edge TTS devolvió audio vacío"
            )
    # ========================================================
    # AZURE SPEECH
    # ========================================================
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
    async def _generate_azure(self, config):
        key, region = config
        url = (
            f"https://{region}."
            "tts.speech.microsoft.com/"
            "cognitiveservices/v1"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": AZURE_OUTPUT_FORMAT,
            "User-Agent": "PenguSpeak/2.0",
        }
        print(
            "[TTS] Generando con Azure Speech | "
            f"Voz: {self.voice}"
        )
        async with aiohttp.ClientSession(
            timeout=AZURE_TIMEOUT
        ) as session:
            async with session.post(
                url,
                headers=headers,
                data=self._build_ssml().encode("utf-8"),
            ) as response:
                if response.status != 200:
                    detail = (
                        await response.text()
                    )[:300]
                    raise RuntimeError(
                        f"Azure HTTP {response.status}: "
                        f"{detail}"
                    )
                async for chunk in (
                    response.content.iter_chunked(8192)
                ):
                    if chunk:
                        self._receive_chunk(
                            chunk,
                            "azure",
                        )
        if not self._chunks:
            raise RuntimeError(
                "Azure Speech devolvió audio vacío"
            )
    # ========================================================
    # SELECCIÓN DE MOTOR
    # ========================================================
    async def _generate(self):
        global _last_edge_failure
        azure_config = get_azure_config()
        try:
            # Edge es el proveedor principal. Si ya falló y Azure
            # está disponible, no se insiste en Edge por cada mensaje.
            trying_edge = _active_engine == "edge" or azure_config is None
            if trying_edge:
                try:
                    await self._generate_edge()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    print(f"[TTS] Error Edge TTS: {exc!r}")
                    _last_edge_failure = time.monotonic()
                    if azure_config is None:
                        raise RuntimeError(
                            "Edge TTS falló y Azure no está configurado"
                        ) from exc
                    # El MP3 progresivo ya puede estar reproduciéndose.
                    # No podemos insertar otro MP3 en mitad del stream.
                    _set_engine("azure")
                    _ensure_recovery_task()
                    if self._chunks:
                        raise RuntimeError(
                            "Edge falló después de comenzar el audio; "
                            "Azure se usará en los siguientes mensajes"
                        ) from exc
                else:
                    # No cambiamos de Azure a Edge aquí: solamente una
                    # prueba de recuperación completa puede hacerlo.
                    pass
            if not self._chunks:
                if azure_config is None:
                    raise RuntimeError("No hay un motor TTS disponible")
                _ensure_recovery_task()
                await self._generate_azure(azure_config)
            self.audio = b"".join(self._chunks)
            self._record_completion()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.error = exc
            print(f"[TTS] Error generando audio: {exc!r}")
        finally:
            self.finished = True
            self._buffer.finish()
            self._buffer_ready.set()
    async def wait_for_first_audio(self):
        if self.task is None:
            self.start()
        await self._buffer_ready.wait()
        if self.error is not None and not self._chunks:
            raise self.error
        if not self._chunks:
            raise RuntimeError(
                "No se recibió audio para reproducir"
            )
        return self._buffer
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
        self._cancelled = True
        self._buffer.finish()
        self._buffer_ready.set()
        if self.task is not None and not self.task.done():
            self.task.cancel()
# ============================================================
# CREAR STREAM
# ============================================================
def create_audio_stream(
    text,
    voice_id,
    started_at=None,
):
    stream = TTSStream(
        text=text,
        voice_id=voice_id,
        started_at=started_at,
    )
    stream.start()
    return stream
# ============================================================
# REPRODUCCIÓN DISCORD
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
        playback_error = None
        try:
            audio_buffer = (
                await stream.wait_for_first_audio()
            )
            if not voice_client.is_connected():
                print(
                    "[TTS] Reproducción cancelada: "
                    "bot desconectado"
                )
                stream.cancel()
                return
            source = discord.FFmpegPCMAudio(
                audio_buffer,
                pipe=True,
                before_options="-f mp3",
                options="-vn",
            )
            def after_playing(error):
                nonlocal playback_error
                playback_error = error
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
            # Esperamos el estado definitivo del generador
            # para distinguir generación de reproducción.
            if stream.task is not None:
                await asyncio.gather(
                    stream.task,
                    return_exceptions=True,
                )
            stats = audio_buffer.stats()
            print(
                "[TTS BUFFER] Resumen | "
                f"Recibidos: {stats['received']} bytes | "
                f"Entregados a FFmpeg: "
                f"{stats['read']} bytes | "
                f"Esperas: {stats['waits']} | "
                f"Máxima: {stats['max_wait_ms']:.0f} ms"
            )
            if stream.error is not None:
                print(
                    "[TTS WARNING] "
                    "Generación incompleta: "
                    f"{stream.error!r}"
                )
            elif playback_error is not None:
                print(
                    "[TTS WARNING] "
                    "La reproducción terminó con error"
                )
            elif stats["read"] < stats["received"]:
                print(
                    "[TTS WARNING] FFmpeg terminó "
                    "sin consumir todos los bytes MP3"
                )
            else:
                print(
                    "[TTS] Reproducción finalizada "
                    "sin errores detectados"
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
            stream.cancel()
        finally:
            if source is not None:
                try:
                    source.cleanup()
                except Exception:
                    pass
            if audio_buffer is not None:
                audio_buffer.close()