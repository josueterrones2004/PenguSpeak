import asyncio
import time


# ============================================================
# CONFIGURACIÓN
# ============================================================

NAME_COOLDOWN = 30
IDLE_DISCONNECT_SECONDS = 300


# ============================================================
# USUARIOS ACTIVOS
# ============================================================

# guild_id -> set(user_id)
active_users = {}


def get_guild_active_users(guild_id):
    if guild_id not in active_users:
        active_users[guild_id] = set()

    return active_users[guild_id]


def activate_user(
    guild_id,
    user_id,
):
    users = get_guild_active_users(
        guild_id
    )

    users.add(
        user_id
    )


def deactivate_user(
    guild_id,
    user_id,
):
    users = get_guild_active_users(
        guild_id
    )

    users.discard(
        user_id
    )


def is_user_active(
    guild_id,
    user_id,
):
    users = get_guild_active_users(
        guild_id
    )

    return user_id in users


def get_guild_active_count(
    guild_id,
):
    return len(
        get_guild_active_users(
            guild_id
        )
    )


def get_total_active_count():
    return sum(
        len(users)
        for users in active_users.values()
    )


# ============================================================
# COLA Y AUDIO
# ============================================================

guild_queues = {}

guild_queue_events = {}

guild_workers = {}

guild_current_items = {}

guild_cancelled_items = {}

guild_audio_locks = {}


def ensure_guild_state(
    guild_id,
):
    from collections import deque

    if guild_id not in guild_queues:
        guild_queues[
            guild_id
        ] = deque()

    if guild_id not in guild_queue_events:
        guild_queue_events[
            guild_id
        ] = asyncio.Event()

    if guild_id not in guild_cancelled_items:
        guild_cancelled_items[
            guild_id
        ] = set()

    if guild_id not in guild_audio_locks:
        guild_audio_locks[
            guild_id
        ] = asyncio.Lock()

    if guild_id not in active_users:
        active_users[
            guild_id
        ] = set()


# ============================================================
# "X DICE"
# ============================================================

last_name_announcement = {}


def should_announce_name(
    guild_id,
    user_id,
):
    key = (
        guild_id,
        user_id,
    )

    now = time.monotonic()

    last_time = (
        last_name_announcement.get(
            key
        )
    )

    if (
        last_time is None
        or now - last_time >= NAME_COOLDOWN
    ):
        last_name_announcement[
            key
        ] = now

        return True

    return False


# ============================================================
# ESTADO DE DISCORD
# ============================================================

async def update_presence(
    bot,
):
    count = (
        get_total_active_count()
    )

    if count == 0:
        text = "Usa /tts iniciar"

    elif count == 1:
        text = "1 usuario usando TTS"

    else:
        text = (
            f"{count} usuarios usando TTS"
        )

    try:
        await bot.change_presence(
            activity=discord.CustomActivity(
                name=text
            )
        )

    except Exception as exc:
        print(
            "No se pudo actualizar "
            f"el estado: {exc}"
        )


# discord se importa aquí para mantener
# organizadas las dependencias del archivo.
import discord


# ============================================================
# DESCONEXIÓN AUTOMÁTICA
# ============================================================

# guild_id -> asyncio.Task
guild_idle_tasks = {}


def cancel_idle_disconnect(
    guild_id,
):
    task = guild_idle_tasks.get(
        guild_id
    )

    if (
        task
        and not task.done()
    ):
        task.cancel()

    guild_idle_tasks.pop(
        guild_id,
        None,
    )


async def idle_disconnect_worker(
    bot,
    guild_id,
):
    try:
        await asyncio.sleep(
            IDLE_DISCONNECT_SECONDS
        )

        # Alguien volvió a activar TTS.
        if (
            get_guild_active_count(
                guild_id
            )
            > 0
        ):
            return

        guild = bot.get_guild(
            guild_id
        )

        if guild is None:
            return

        voice_client = (
            guild.voice_client
        )

        # Limpiar mensajes que pudieran
        # haberse quedado pendientes.
        queue = guild_queues.get(
            guild_id
        )

        if queue is not None:
            queue.clear()

        event = guild_queue_events.get(
            guild_id
        )

        if event is not None:
            event.clear()

        # Cortar cualquier audio que siga
        # reproduciéndose.
        if (
            voice_client
            and voice_client.is_playing()
        ):
            voice_client.stop()

        if (
            voice_client
            and voice_client.is_connected()
        ):
            await voice_client.disconnect(
                force=True
            )

            print(
                "[VOICE] Desconectado "
                "por 5 minutos de inactividad."
            )

    except asyncio.CancelledError:
        # Alguien volvió a utilizar el bot
        # antes de que pasaran los 5 minutos.
        pass

    except Exception as exc:
        print(
            "Error en desconexión "
            f"automática: {exc}"
        )

    finally:
        current = guild_idle_tasks.get(
            guild_id
        )

        if current is asyncio.current_task():
            guild_idle_tasks.pop(
                guild_id,
                None,
            )


def schedule_idle_disconnect(
    bot,
    guild_id,
):
    # Reinicia el contador.
    cancel_idle_disconnect(
        guild_id
    )

    guild_idle_tasks[
        guild_id
    ] = asyncio.create_task(
        idle_disconnect_worker(
            bot,
            guild_id,
        )
    )
