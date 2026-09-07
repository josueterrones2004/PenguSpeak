import asyncio
import os
import uuid

from penguspeak.audio import (
    create_audio_file,
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
# AÑADIR A COLA
# ============================================================

def add_to_queue(
    guild_id,
    user_id,
    text,
    voice_id,
):
    ensure_guild_state(
        guild_id
    )

    item = {
        "id": uuid.uuid4().hex,
        "user_id": user_id,
        "text": text,
        "voice_id": voice_id,
    }

    guild_queues[
        guild_id
    ].append(
        item
    )

    # Cada nuevo mensaje reinicia
    # el contador de inactividad.
    mark_guild_activity(
        guild_id
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
        if item["user_id"] == user_id:
            return queue.pop(
                index
            )

    return None


# ============================================================
# WORKER DE COLA
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

    cancelled = (
        guild_cancelled_items[
            guild_id
        ]
    )

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

            filepath = None

            try:
                # --------------------------------------------
                # CANCELADO ANTES DE GENERAR
                # --------------------------------------------

                if item_id in cancelled:
                    cancelled.discard(
                        item_id
                    )

                    continue

                guild = bot.get_guild(
                    guild_id
                )

                if guild is None:
                    continue

                voice_client = (
                    guild.voice_client
                )

                if (
                    voice_client is None
                    or not voice_client.is_connected()
                ):
                    continue

                # Mientras haya trabajo,
                # el bot sigue considerándose activo.
                mark_guild_activity(
                    guild_id
                )

                # --------------------------------------------
                # GENERAR AUDIO
                # --------------------------------------------

                filepath = (
                    await create_audio_file(
                        item["text"],
                        item["voice_id"],
                    )
                )

                if not filepath:
                    continue

                # --------------------------------------------
                # CANCELADO DURANTE GENERACIÓN
                # --------------------------------------------

                if item_id in cancelled:
                    cancelled.discard(
                        item_id
                    )

                    try:
                        os.remove(
                            filepath
                        )

                    except FileNotFoundError:
                        pass

                    filepath = None

                    continue

                # --------------------------------------------
                # REPRODUCIR
                # --------------------------------------------

                mark_guild_activity(
                    guild_id
                )

                await play_audio(
                    bot,
                    guild_id,
                    voice_client,
                    filepath,
                )

                filepath = None

                mark_guild_activity(
                    guild_id
                )

            except asyncio.CancelledError:
                raise

            except Exception as exc:
                print(
                    "[QUEUE] Error procesando audio: "
                    f"{exc}"
                )

            finally:
                if filepath:
                    try:
                        os.remove(
                            filepath
                        )

                    except FileNotFoundError:
                        pass

                guild_current_items[
                    guild_id
                ] = None

                cancelled.discard(
                    item_id
                )

        event.clear()

        # Por si se añadió un elemento justo
        # entre el último chequeo y clear().
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

    # El monitor de 5 minutos se crea
    # al mismo tiempo que el worker.
    schedule_idle_disconnect(
        bot,
        guild_id,
    )
