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
)


# ============================================================
# AÑADIR A LA COLA
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
        "id": str(
            uuid.uuid4()
        ),
        "user_id": user_id,
        "text": text,
        "voice_id": voice_id,
    }

    guild_queues[
        guild_id
    ].append(
        item
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

    for item in list(
        queue
    ):
        if (
            item["user_id"]
            == user_id
        ):
            queue.remove(
                item
            )

            return item

    return None


# ============================================================
# WORKER DE LA COLA
# ============================================================

async def guild_queue_worker(
    bot,
    guild_id,
):
    ensure_guild_state(
        guild_id
    )

    while True:
        queue = guild_queues[
            guild_id
        ]

        if not queue:
            guild_queue_events[
                guild_id
            ].clear()

            await guild_queue_events[
                guild_id
            ].wait()

            continue

        item = queue.popleft()

        guild_current_items[
            guild_id
        ] = item

        cancelled = guild_cancelled_items[
            guild_id
        ]

        if item["id"] in cancelled:
            cancelled.discard(
                item["id"]
            )

            guild_current_items[
                guild_id
            ] = None

            continue

        guild = bot.get_guild(
            guild_id
        )

        if not guild:
            guild_current_items[
                guild_id
            ] = None

            continue

        voice_client = (
            guild.voice_client
        )

        if (
            not voice_client
            or not voice_client.is_connected()
        ):
            guild_current_items[
                guild_id
            ] = None

            continue

        filepath = None

        try:
            print(
                "[QUEUE] "
                f"{item['user_id']} "
                f"[{item['voice_id']}]: "
                f"{item['text']}"
            )

            filepath = (
                await create_audio_file(
                    item["text"],
                    item["voice_id"],
                )
            )

            if not filepath:
                continue

            # Puede haberse usado /tts saltar
            # mientras se generaba el audio.
            if item["id"] in cancelled:
                cancelled.discard(
                    item["id"]
                )

                continue

            await play_audio(
                bot,
                guild_id,
                voice_client,
                filepath,
            )

            filepath = None

            # Si se usó /tts saltar mientras
            # se reproducía el audio.
            if item["id"] in cancelled:
                cancelled.discard(
                    item["id"]
                )

        except Exception as exc:
            print(
                "Error en la cola: "
                f"{exc}"
            )

        finally:
            guild_current_items[
                guild_id
            ] = None

            if (
                filepath
                and os.path.exists(
                    filepath
                )
            ):
                try:
                    os.remove(
                        filepath
                    )

                except OSError:
                    pass


# ============================================================
# ASEGURAR WORKER
# ============================================================

def ensure_guild_worker(
    bot,
    guild_id,
):
    ensure_guild_state(
        guild_id
    )

    task = guild_workers.get(
        guild_id
    )

    if (
        task is None
        or task.done()
    ):
        guild_workers[
            guild_id
        ] = asyncio.create_task(
            guild_queue_worker(
                bot,
                guild_id,
            )
        )
