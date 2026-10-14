import asyncio
import time
import uuid
from penguspeak.audio import (
    create_audio_stream,
    play_audio,
)
from penguspeak.state import (
    guild_cancelled_items,
    guild_current_items,
    guild_queue_events,
    guild_queues,
    guild_workers,
    guild_voice_locks,
    guild_session_channels,
    get_guild_active_count,
    ensure_guild_state,
    mark_guild_activity,
    schedule_idle_disconnect,
)
# ============================================================
# PREPARAR STREAM
# ============================================================
def ensure_item_stream(
    guild_id,
    item,
):
    if item.get(
        "removed",
        False,
    ):
        return None
    existing = item.get(
        "stream"
    )
    if existing is not None:
        return existing
    try:
        stream = create_audio_stream(
            text=item["text"],
            voice_id=item["voice_id"],
            started_at=item["started_at"],
        )
    except Exception as exc:
        print(
            "[QUEUE] Error creando stream: "
            f"{exc}"
        )
        return None
    item[
        "stream"
    ] = stream
    print(
        "[QUEUE] Stream iniciado: "
        f"{item['id'][:8]}"
    )
    return stream
# ============================================================
# CANCELAR STREAM
# ============================================================
def cancel_item_stream(
    item,
):
    stream = item.get(
        "stream"
    )
    if stream is None:
        return
    try:
        stream.cancel()
    except Exception as exc:
        print(
            "[QUEUE] Error cancelando stream: "
            f"{exc}"
        )
def clear_guild_queue(guild_id):
    """Cancelar los streams pendientes sin tocar el mensaje actual."""
    queue = guild_queues.get(guild_id, [])
    for item in queue:
        item["removed"] = True
        cancel_item_stream(item)
    queue.clear()
    event = guild_queue_events.get(guild_id)
    if event is not None:
        event.clear()


async def reconnect_guild_voice(bot, guild_id, attempts=3):
    """Reconectar únicamente al canal de la sesión original."""
    guild = bot.get_guild(guild_id)
    channel_id = guild_session_channels.get(guild_id)
    if guild is None or channel_id is None:
        return None
    channel = guild.get_channel(channel_id)
    if channel is None:
        return None
    ensure_guild_state(guild_id)
    async with guild_voice_locks[guild_id]:
        client = guild.voice_client
        if client is not None and client.is_connected():
            return client if client.channel and client.channel.id == channel_id else None
        for attempt in range(attempts):
            try:
                if client is not None:
                    try:
                        await client.disconnect(force=True)
                    except Exception:
                        pass
                client = await channel.connect(self_deaf=True, timeout=12.0, reconnect=True)
                await guild.change_voice_state(channel=channel, self_deaf=True)
                return client
            except (asyncio.CancelledError, KeyboardInterrupt):
                raise
            except Exception as exc:
                print(f"[VOICE] Reconexión {attempt + 1}/{attempts} en {guild_id}: {exc}")
                if attempt + 1 < attempts:
                    await asyncio.sleep(2)
        return None


# ============================================================
# AÑADIR A COLA
# ============================================================
def add_to_queue(
    guild_id,
    user_id,
    text,
    voice_id,
    started_at=None,
):
    ensure_guild_state(
        guild_id
    )
    if started_at is None:
        started_at = (
            time.perf_counter()
        )
    item = {
        "id": uuid.uuid4().hex,
        "user_id": user_id,
        "text": text,
        "voice_id": voice_id,
        "started_at": started_at,
        "stream": None,
        "removed": False,
    }
    queue = guild_queues[
        guild_id
    ]
    queue.append(
        item
    )
    mark_guild_activity(
        guild_id
    )
    # El primer mensaje pendiente comienza a generarse
    # inmediatamente.
    if len(queue) == 1:
        ensure_item_stream(
            guild_id,
            item,
        )
    guild_queue_events[
        guild_id
    ].set()
    return item
# ============================================================
# ELIMINAR PRÓXIMO MENSAJE DE UN USUARIO
# ============================================================
def remove_next_user_item(
    guild_id,
    user_id,
):
    ensure_guild_state(
        guild_id
    )
    queue = guild_queues[
        guild_id
    ]
    for index, item in enumerate(
        queue
    ):
        if (
            item["user_id"]
            == user_id
        ):
            removed = queue.pop(
                index
            )
            removed[
                "removed"
            ] = True
            cancel_item_stream(
                removed
            )
            if (
                index == 0
                and queue
            ):
                ensure_item_stream(
                    guild_id,
                    queue[0],
                )
            return removed
    return None
# ============================================================
# ELIMINAR TODOS LOS MENSAJES DE UN USUARIO
# ============================================================
def remove_all_user_items(
    guild_id,
    user_id,
):
    """
    Usado por /tts detener.
    Elimina todos los mensajes pendientes del usuario
    sin iniciar y cancelar prefetched streams uno por uno.
    """
    ensure_guild_state(
        guild_id
    )
    queue = guild_queues[
        guild_id
    ]
    kept = []
    removed = []
    for item in queue:
        if (
            item["user_id"]
            == user_id
        ):
            item[
                "removed"
            ] = True
            cancel_item_stream(
                item
            )
            removed.append(
                item
            )
        else:
            kept.append(
                item
            )
    queue[:] = kept
    # Preparamos el nuevo primero, si existe.
    if queue:
        ensure_item_stream(
            guild_id,
            queue[0],
        )
    return len(
        removed
    )
# ============================================================
# WORKER
# ============================================================
async def guild_queue_worker(
    bot,
    guild_id,
):
    ensure_guild_state(
        guild_id
    )
    event = guild_queue_events[
        guild_id
    ]
    queue = guild_queues[
        guild_id
    ]
    cancelled = guild_cancelled_items[
        guild_id
    ]
    while True:
        await event.wait()
        event.clear()
        while queue:
            item = queue.pop(
                0
            )
            item_id = item[
                "id"
            ]
            guild_current_items[
                guild_id
            ] = item
            try:
                # --------------------------------------------
                # CANCELADO
                # --------------------------------------------
                if (
                    item_id in cancelled
                    or item.get(
                        "removed",
                        False,
                    )
                ):
                    cancelled.discard(
                        item_id
                    )
                    cancel_item_stream(
                        item
                    )
                    continue
                # --------------------------------------------
                # SERVIDOR
                # --------------------------------------------
                guild = bot.get_guild(
                    guild_id
                )
                if guild is None:
                    cancel_item_stream(
                        item
                    )
                    continue
                # --------------------------------------------
                # VOZ
                # --------------------------------------------
                voice_client = (
                    guild.voice_client
                )
                if voice_client is None or not voice_client.is_connected():
                    if get_guild_active_count(guild_id) > 0:
                        voice_client = await reconnect_guild_voice(bot, guild_id)
                    if voice_client is None or not voice_client.is_connected():
                        if get_guild_active_count(guild_id) > 0 and guild_session_channels.get(guild_id):
                            # Mantener el mensaje en cola para un próximo intento.
                            queue.insert(0, item)
                            guild_current_items[guild_id] = None
                            await asyncio.sleep(5)
                            continue
                        cancel_item_stream(item)
                        continue
                mark_guild_activity(
                    guild_id
                )
                # --------------------------------------------
                # STREAM ACTUAL
                # --------------------------------------------
                stream = ensure_item_stream(
                    guild_id,
                    item,
                )
                if stream is None:
                    continue
                # --------------------------------------------
                # PREFETCH DEL SIGUIENTE
                # --------------------------------------------
                if queue:
                    ensure_item_stream(
                        guild_id,
                        queue[0],
                    )
                # --------------------------------------------
                # CANCELADO ANTES DE PLAY
                # --------------------------------------------
                if item_id in cancelled:
                    cancelled.discard(
                        item_id
                    )
                    cancel_item_stream(
                        item
                    )
                    continue
                # --------------------------------------------
                # PLAY
                # --------------------------------------------
                mark_guild_activity(
                    guild_id
                )
                await play_audio(
                    bot,
                    guild_id,
                    voice_client,
                    stream,
                )
                mark_guild_activity(
                    guild_id
                )
            except asyncio.CancelledError:
                cancel_item_stream(
                    item
                )
                raise
            except Exception as exc:
                print(
                    "[QUEUE] Error procesando audio: "
                    f"{exc}"
                )
                cancel_item_stream(
                    item
                )
            finally:
                guild_current_items[
                    guild_id
                ] = None
                cancelled.discard(
                    item_id
                )
        # Si hubo entradas nuevas durante el procesamiento,
        # add_to_queue ya habrá activado el evento.
# ============================================================
# CREAR WORKER
# ============================================================
def ensure_guild_worker(
    bot,
    guild_id,
):
    ensure_guild_state(
        guild_id
    )
    worker = guild_workers.get(
        guild_id
    )
    if (
        worker is None
        or worker.done()
    ):
        guild_workers[
            guild_id
        ] = asyncio.create_task(
            guild_queue_worker(
                bot,
                guild_id,
            )
        )
    schedule_idle_disconnect(
        bot,
        guild_id,
    )
