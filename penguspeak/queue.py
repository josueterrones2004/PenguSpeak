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
# ARCHIVOS
# ============================================================

def remove_audio_file(
    filepath,
):
    if not filepath:
        return

    try:
        os.remove(
            filepath
        )

    except FileNotFoundError:
        pass

    except Exception as exc:
        print(
            "[QUEUE] Error eliminando "
            f"archivo temporal: {exc}"
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

        # Prefetch
        "prefetch_task": None,
        "prefetched_filepath": None,

        # Se marca cuando /tts saltar
        # elimina el elemento antes de reproducirlo.
        "removed": False,
    }

    guild_queues[
        guild_id
    ].append(
        item
    )

    mark_guild_activity(
        guild_id
    )

    guild_queue_events[
        guild_id
    ].set()

    return item


# ============================================================
# GENERACIÓN ANTICIPADA
# ============================================================

async def generate_prefetched_audio(
    guild_id,
    item,
):
    """
    Genera el audio de un elemento todavía en cola.

    Si /tts saltar elimina el mensaje mientras se
    está generando, el archivo se elimina cuando
    termine la generación.
    """

    if item.get(
        "removed",
        False,
    ):
        return None

    try:
        mark_guild_activity(
            guild_id
        )

        filepath = (
            await create_audio_file(
                item["text"],
                item["voice_id"],
            )
        )

        if not filepath:
            return None

        # El mensaje pudo ser eliminado mientras
        # Edge TTS estaba generando el archivo.
        if item.get(
            "removed",
            False,
        ):
            remove_audio_file(
                filepath
            )

            return None

        item[
            "prefetched_filepath"
        ] = filepath

        print(
            "[QUEUE] Prefetch listo: "
            f"{item['id'][:8]}"
        )

        return filepath

    except asyncio.CancelledError:
        raise

    except Exception as exc:
        print(
            "[QUEUE] Error en prefetch: "
            f"{exc}"
        )

        return None


def ensure_item_prefetch(
    guild_id,
    item,
):
    """
    Garantiza que un mensaje tenga como máximo
    una tarea de prefetch.
    """

    if item.get(
        "removed",
        False,
    ):
        return None

    if item.get(
        "prefetched_filepath"
    ):
        return None

    task = item.get(
        "prefetch_task"
    )

    if (
        task is not None
        and not task.done()
    ):
        return task

    # Si una tarea anterior ya terminó pero dejó
    # un archivo listo, no generamos de nuevo.
    if (
        task is not None
        and task.done()
        and item.get(
            "prefetched_filepath"
        )
    ):
        return task

    task = asyncio.create_task(
        generate_prefetched_audio(
            guild_id,
            item,
        )
    )

    item[
        "prefetch_task"
    ] = task

    return task


async def watch_for_next_item(
    guild_id,
    queue,
):
    """
    Se ejecuta mientras el mensaje actual está
    reproduciéndose.

    Si ya existe otro elemento, empieza su
    generación inmediatamente.

    Si la cola está vacía, espera a que llegue
    uno mientras el audio actual siga sonando.
    """

    try:
        while True:
            if queue:
                next_item = queue[0]

                if not next_item.get(
                    "removed",
                    False,
                ):
                    ensure_item_prefetch(
                        guild_id,
                        next_item,
                    )

                    return

            await asyncio.sleep(
                0.1
            )

    except asyncio.CancelledError:
        return


# ============================================================
# OBTENER AUDIO DEL ELEMENTO
# ============================================================

async def get_item_audio(
    guild_id,
    item,
):
    """
    Usa el audio prefetched si ya existe.

    Si todavía se está generando, espera a esa misma
    tarea para evitar generar el mismo audio dos veces.

    Si no había prefetch, lo genera normalmente.
    """

    filepath = item.get(
        "prefetched_filepath"
    )

    if filepath:
        item[
            "prefetched_filepath"
        ] = None

        return filepath

    task = item.get(
        "prefetch_task"
    )

    if task is not None:
        try:
            filepath = await task

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            print(
                "[QUEUE] Error esperando "
                f"prefetch: {exc}"
            )

            filepath = None

        item[
            "prefetch_task"
        ] = None

        # generate_prefetched_audio también guarda
        # la ruta dentro del item.
        prefetched = item.get(
            "prefetched_filepath"
        )

        if prefetched:
            item[
                "prefetched_filepath"
            ] = None

            return prefetched

        if filepath:
            return filepath

    # No existía ningún prefetch.
    mark_guild_activity(
        guild_id
    )

    return await create_audio_file(
        item["text"],
        item["voice_id"],
    )


# ============================================================
# LIMPIAR PREFETCH DE UN ELEMENTO
# ============================================================

async def cleanup_item_prefetch(
    item,
):
    item[
        "removed"
    ] = True

    task = item.get(
        "prefetch_task"
    )

    if (
        task is not None
        and not task.done()
    ):
        # No cancelamos Edge TTS a mitad de generación.
        #
        # generate_prefetched_audio verá "removed"
        # al terminar y eliminará su archivo.
        return

    filepath = item.get(
        "prefetched_filepath"
    )

    if filepath:
        remove_audio_file(
            filepath
        )

        item[
            "prefetched_filepath"
        ] = None


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

            # Si el archivo ya estaba generado,
            # podemos borrarlo inmediatamente.
            filepath = removed.get(
                "prefetched_filepath"
            )

            if filepath:
                remove_audio_file(
                    filepath
                )

                removed[
                    "prefetched_filepath"
                ] = None

            return removed

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
            prefetch_watcher = None

            try:
                # --------------------------------------------
                # CANCELADO ANTES DE REPRODUCIR
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

                    await cleanup_item_prefetch(
                        item
                    )

                    continue

                guild = bot.get_guild(
                    guild_id
                )

                if guild is None:
                    await cleanup_item_prefetch(
                        item
                    )

                    continue

                voice_client = (
                    guild.voice_client
                )

                if (
                    voice_client is None
                    or not voice_client.is_connected()
                ):
                    await cleanup_item_prefetch(
                        item
                    )

                    continue

                mark_guild_activity(
                    guild_id
                )

                # --------------------------------------------
                # OBTENER AUDIO
                #
                # Puede estar:
                # - ya generado
                # - generándose
                # - sin empezar todavía
                # --------------------------------------------

                filepath = (
                    await get_item_audio(
                        guild_id,
                        item,
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

                    remove_audio_file(
                        filepath
                    )

                    filepath = None

                    continue

                # --------------------------------------------
                # PREFETCH DEL SIGUIENTE
                #
                # Este watcher vive mientras el audio actual
                # se está reproduciendo.
                # --------------------------------------------

                prefetch_watcher = (
                    asyncio.create_task(
                        watch_for_next_item(
                            guild_id,
                            queue,
                        )
                    )
                )

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
                if prefetch_watcher:
                    if not prefetch_watcher.done():
                        prefetch_watcher.cancel()

                    try:
                        await prefetch_watcher

                    except asyncio.CancelledError:
                        pass

                if filepath:
                    remove_audio_file(
                        filepath
                    )

                guild_current_items[
                    guild_id
                ] = None

                cancelled.discard(
                    item_id
                )

        event.clear()

        # Por si entró algo justo entre el último
        # chequeo de la cola y event.clear().
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
