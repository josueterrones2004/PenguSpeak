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

                if (
                    voice_client is None
                    or not voice_client.is_connected()
                ):
                    cancel_item_stream(
                        item
                    )

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

        event.clear()

        # Evita perder un mensaje que haya entrado justo
        # antes de limpiar el Event.
        if queue:
            event.set()


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