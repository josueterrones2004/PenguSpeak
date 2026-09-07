import asyncio
import time

import discord


NAME_COOLDOWN = 30
IDLE_DISCONNECT_SECONDS = 300


# ============================================================
# USUARIOS CON TTS ACTIVO
# ============================================================

active_users = {}


def get_guild_active_users(guild_id):
    return active_users.setdefault(
        guild_id,
        set(),
    )


def activate_user(
    guild_id,
    user_id,
):
    get_guild_active_users(
        guild_id
    ).add(
        user_id
    )


def deactivate_user(
    guild_id,
    user_id,
):
    get_guild_active_users(
        guild_id
    ).discard(
        user_id
    )


def clear_guild_active_users(
    guild_id,
):
    get_guild_active_users(
        guild_id
    ).clear()


def is_user_active(
    guild_id,
    user_id,
):
    return (
        user_id
        in get_guild_active_users(
            guild_id
        )
    )


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


def has_active_user_in_voice(
    guild,
):
    """
    Devuelve True si al menos uno de los usuarios
    que tiene TTS activo sigue actualmente dentro
    de algún canal de voz.
    """

    guild_id = guild.id

    for user_id in get_guild_active_users(
        guild_id
    ):
        member = guild.get_member(
            user_id
        )

        if (
            member
            and member.voice
            and member.voice.channel
        ):
            return True

    return False


# ============================================================
# COLAS
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
    guild_queues.setdefault(
        guild_id,
        [],
    )

    guild_queue_events.setdefault(
        guild_id,
        asyncio.Event(),
    )

    guild_current_items.setdefault(
        guild_id,
        None,
    )

    guild_cancelled_items.setdefault(
        guild_id,
        set(),
    )

    guild_audio_locks.setdefault(
        guild_id,
        asyncio.Lock(),
    )


# ============================================================
# ANUNCIO DE NOMBRES
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

    previous = (
        last_name_announcement.get(
            key
        )
    )

    if (
        previous is None
        or now - previous
        >= NAME_COOLDOWN
    ):
        last_name_announcement[
            key
        ] = now

        return True

    return False


# ============================================================
# ACTIVIDAD / INACTIVIDAD
# ============================================================

guild_last_activity = {}
guild_idle_tasks = {}


def mark_guild_activity(
    guild_id,
):
    guild_last_activity[
        guild_id
    ] = time.monotonic()


def cancel_idle_disconnect(
    guild_id,
):
    """
    Actualmente esta función reinicia el contador
    de inactividad.

    El monitor permanece activo.
    """

    mark_guild_activity(
        guild_id
    )


async def idle_disconnect_worker(
    bot,
    guild_id,
):
    ensure_guild_state(
        guild_id
    )

    mark_guild_activity(
        guild_id
    )

    try:
        while True:
            guild = bot.get_guild(
                guild_id
            )

            if guild is None:
                return

            voice_client = (
                guild.voice_client
            )

            if (
                voice_client is None
                or not voice_client.is_connected()
            ):
                return

            # ------------------------------------------------
            # TODAVÍA HAY AUDIO O MENSAJES PENDIENTES
            # ------------------------------------------------

            queue_busy = bool(
                guild_queues.get(
                    guild_id
                )
            )

            current_busy = (
                guild_current_items.get(
                    guild_id
                )
                is not None
            )

            playing = (
                voice_client.is_playing()
            )

            if (
                queue_busy
                or current_busy
                or playing
            ):
                mark_guild_activity(
                    guild_id
                )

                await asyncio.sleep(
                    5
                )

                continue

            # ------------------------------------------------
            # TIEMPO SIN ACTIVIDAD
            # ------------------------------------------------

            last_activity = (
                guild_last_activity.get(
                    guild_id,
                    time.monotonic(),
                )
            )

            idle_for = (
                time.monotonic()
                - last_activity
            )

            remaining = (
                IDLE_DISCONNECT_SECONDS
                - idle_for
            )

            if remaining > 0:
                await asyncio.sleep(
                    min(
                        5,
                        remaining,
                    )
                )

                continue

            # ------------------------------------------------
            # 5 MINUTOS SIN ACTIVIDAD
            # ------------------------------------------------

            print(
                f"[IDLE] Servidor {guild_id}: "
                "5 minutos sin actividad. "
                "Desconectando de voz..."
            )

            guild_queues[
                guild_id
            ].clear()

            guild_queue_events[
                guild_id
            ].clear()

            current = (
                guild_current_items.get(
                    guild_id
                )
            )

            if current is not None:
                guild_cancelled_items[
                    guild_id
                ].add(
                    current["id"]
                )

            if voice_client.is_playing():
                voice_client.stop()

            # IMPORTANTE:
            #
            # NO borramos active_users.
            #
            # Los usuarios siguen teniendo TTS activo
            # aunque PenguSpeak salga por inactividad.

            try:
                await voice_client.disconnect(
                    force=True
                )

            except Exception as exc:
                print(
                    "[IDLE] Error al desconectar: "
                    f"{exc}"
                )

            print(
                f"[IDLE] Servidor {guild_id}: "
                "usuarios TTS conservados. "
                "Se reconectará cuando vuelvan "
                "a escribir."
            )

            return

    except asyncio.CancelledError:
        return

    finally:
        current_task = (
            guild_idle_tasks.get(
                guild_id
            )
        )

        if (
            current_task
            is asyncio.current_task()
        ):
            guild_idle_tasks.pop(
                guild_id,
                None,
            )


def schedule_idle_disconnect(
    bot,
    guild_id,
):
    ensure_guild_state(
        guild_id
    )

    task = guild_idle_tasks.get(
        guild_id
    )

    if (
        task
        and not task.done()
    ):
        return

    mark_guild_activity(
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


# ============================================================
# PRESENCIA
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

    await bot.change_presence(
        activity=discord.CustomActivity(
            name=text
        )
    )
