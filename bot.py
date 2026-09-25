import asyncio
import inspect
import signal
import time

import discord
from discord import app_commands
from discord.ext import commands

from config import DISCORD_TOKEN

from penguspeak.database import (
    get_nickname,
    get_user_voice,
    init_database,
    remove_nickname,
    set_nickname,
)

from penguspeak.ocr import (
    get_attachment_ocr_text,
    is_supported_image,
)

from penguspeak.queue import (
    add_to_queue,
    ensure_guild_worker,
    remove_all_user_items,
    remove_next_user_item,
)

from penguspeak.state import (
    activate_user,
    cancel_idle_disconnect,
    deactivate_user,
    ensure_guild_state,
    get_guild_active_count,
    get_guild_active_users,
    guild_cancelled_items,
    guild_current_items,
    is_user_active,
    schedule_idle_disconnect,
    update_presence,
)

from penguspeak.text import (
    build_spoken_message,
    is_valid_nickname,
    normalize_spaces,
)

from penguspeak.views import (
    VoiceBrowserView,
)

from penguspeak.voices import (
    VOICES,
    get_voice_label,
)


# ============================================================
# BOT
# ============================================================

intents = discord.Intents.default()

intents.guilds = True
intents.voice_states = True
intents.messages = True
intents.message_content = True


class PenguSpeakBot(
    commands.Bot
):
    async def setup_hook(
        self,
    ):
        init_database()

        register_signal_handlers()

        synced = (
            await self.tree.sync()
        )

        root_names = {
            command.name
            for command in synced
        }

        print(
            f"{len(root_names)} grupos "
            "de comandos sincronizados."
        )


bot = PenguSpeakBot(
    command_prefix="!",
    intents=intents,
)


# ============================================================
# GRUPOS DE COMANDOS
# ============================================================

tts_group = app_commands.Group(
    name="tts",
    description=(
        "Comandos de texto a voz."
    ),
)

voz_group = app_commands.Group(
    name="voz",
    description=(
        "Consulta tu voz actual."
    ),
)

voces_group = app_commands.Group(
    name="voces",
    description=(
        "Explora y selecciona voces."
    ),
)

apodo_group = app_commands.Group(
    name="apodo",
    description=(
        "Configura tu nombre para TTS."
    ),
)


# ============================================================
# CIERRE LIMPIO
# ============================================================

shutdown_started = False


async def shutdown_bot():
    global shutdown_started

    if shutdown_started:
        return

    shutdown_started = True

    print(
        "[SHUTDOWN] Cerrando PenguSpeak..."
    )

    for voice_client in list(
        bot.voice_clients
    ):
        try:
            if voice_client.is_playing():
                voice_client.stop()

            await voice_client.disconnect(
                force=True
            )

        except Exception as exc:
            print(
                "[SHUTDOWN] Error "
                "desconectando voz: "
                f"{exc}"
            )

    try:
        await bot.close()

    except Exception as exc:
        print(
            "[SHUTDOWN] Error cerrando bot: "
            f"{exc}"
        )


def register_signal_handlers():
    try:
        loop = (
            asyncio.get_running_loop()
        )

    except RuntimeError:
        return

    for sig in (
        signal.SIGINT,
        signal.SIGTERM,
        signal.SIGHUP,
    ):
        try:
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(
                    shutdown_bot()
                ),
            )

        except (
            NotImplementedError,
            RuntimeError,
        ):
            pass


# ============================================================
# UTILIDADES DE VOZ
# ============================================================

async def ensure_self_deaf(
    guild,
    channel,
):
    """
    Fuerza self_deaf=True.

    También se usa después de mover el bot de canal,
    porque Discord puede perder el estado de
    ensordecido durante el movimiento.
    """

    try:
        await guild.change_voice_state(
            channel=channel,
            self_deaf=True,
        )

    except Exception as exc:
        print(
            "[VOICE] No pude aplicar "
            f"self_deaf: {exc}"
        )


async def get_voice_client(
    interaction,
):
    if not interaction.guild:
        return None

    member = (
        interaction.user
    )

    if not isinstance(
        member,
        discord.Member,
    ):
        return None

    if (
        not member.voice
        or not member.voice.channel
    ):
        return None

    guild = (
        interaction.guild
    )

    channel = (
        member.voice.channel
    )

    guild_id = (
        guild.id
    )

    cancel_idle_disconnect(
        guild_id
    )

    voice_client = (
        guild.voice_client
    )

    # --------------------------------------------------------
    # CONECTAR
    # --------------------------------------------------------

    if (
        voice_client is None
        or not voice_client.is_connected()
    ):
        voice_client = (
            await channel.connect(
                self_deaf=True
            )
        )

        await ensure_self_deaf(
            guild,
            channel,
        )

        ensure_guild_worker(
            bot,
            guild_id,
        )

        return voice_client

    # --------------------------------------------------------
    # MOVER
    # --------------------------------------------------------

    if (
        voice_client.channel
        != channel
    ):
        await voice_client.move_to(
            channel
        )

        await ensure_self_deaf(
            guild,
            channel,
        )

    ensure_guild_worker(
        bot,
        guild_id,
    )

    return voice_client


# ============================================================
# COMPROBAR USUARIOS TTS EN VOZ
# ============================================================

def guild_has_active_user_in_voice(
    guild,
):
    guild_id = (
        guild.id
    )

    for user_id in (
        get_guild_active_users(
            guild_id
        )
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
# READY
# ============================================================

@bot.event
async def on_ready():
    print(
        f"PenguSpeak conectado como "
        f"{bot.user}"
    )

    if bot.user:
        print(
            f"ID: {bot.user.id}"
        )

    await update_presence(
        bot
    )


# ============================================================
# CAMBIOS DE CANAL DE VOZ
# ============================================================

@bot.event
async def on_voice_state_update(
    member,
    before,
    after,
):
    if member.bot:
        return

    guild = (
        member.guild
    )

    guild_id = (
        guild.id
    )

    if not is_user_active(
        guild_id,
        member.id,
    ):
        return

    # --------------------------------------------------------
    # TODAVÍA HAY ALGÚN USUARIO TTS EN VOZ
    # --------------------------------------------------------

    if guild_has_active_user_in_voice(
        guild
    ):
        return

    # --------------------------------------------------------
    # EL ÚLTIMO USUARIO TTS SALIÓ DE VOZ
    # --------------------------------------------------------

    get_guild_active_users(
        guild_id
    ).clear()

    voice_client = (
        guild.voice_client
    )

    if (
        voice_client
        and voice_client.is_connected()
    ):
        if voice_client.is_playing():
            voice_client.stop()

        try:
            await voice_client.disconnect(
                force=True
            )

        except Exception as exc:
            print(
                "[VOICE] Error "
                "desconectando: "
                f"{exc}"
            )

    await update_presence(
        bot
    )

    print(
        f"[VOICE] Servidor {guild_id}: "
        "último usuario TTS salió de voz. "
        "Sesión terminada."
    )


# ============================================================
# MENSAJES DEL MODO CONTINUO
# ============================================================

@bot.event
async def on_message(
    message,
):
    # Momento exacto en el que discord.py nos entrega
    # el mensaje.
    received_at = time.perf_counter()

    if message.author.bot:
        return

    if not message.guild:
        return

    guild = (
        message.guild
    )

    guild_id = (
        guild.id
    )

    user_id = (
        message.author.id
    )

    # --------------------------------------------------------
    # SOLO USUARIOS CON /tts iniciar
    # --------------------------------------------------------

    if not is_user_active(
        guild_id,
        user_id,
    ):
        return

    if not isinstance(
        message.author,
        discord.Member,
    ):
        return

    # --------------------------------------------------------
    # EL USUARIO DEBE SEGUIR EN VOZ
    # --------------------------------------------------------

    if (
        not message.author.voice
        or not message.author.voice.channel
    ):
        return

    user_channel = (
        message.author.voice.channel
    )

    voice_client = (
        guild.voice_client
    )

    # --------------------------------------------------------
    # RECONEXIÓN AUTOMÁTICA
    # --------------------------------------------------------

    if (
        voice_client is None
        or not voice_client.is_connected()
    ):
        try:
            print(
                "[VOICE] Reconectando "
                "automáticamente a "
                f"{user_channel.name}..."
            )

            voice_client = (
                await user_channel.connect(
                    self_deaf=True
                )
            )

            await ensure_self_deaf(
                guild,
                user_channel,
            )

            print(
                "[VOICE] Reconectado "
                "automáticamente."
            )

        except Exception as exc:
            print(
                "[VOICE] Error en reconexión "
                f"automática: {exc}"
            )

            return

    # --------------------------------------------------------
    # ESTÁ EN OTRO CANAL
    # --------------------------------------------------------

    if (
        voice_client.channel
        != user_channel
    ):
        return

    ensure_guild_worker(
        bot,
        guild_id,
    )

    cancel_idle_disconnect(
        guild_id
    )

    # --------------------------------------------------------
    # CONSTRUIR MENSAJE
    # --------------------------------------------------------

    text = (
        await build_spoken_message(
            message
        )
    )

    processed_at = time.perf_counter()

    print(
        "[TTS PERF] "
        "Discord -> texto listo: "
        f"{(processed_at - received_at) * 1000:.0f} ms"
    )

    if not text:
        return

    voice_id = get_user_voice(
        user_id,
        VOICES,
    )

    # --------------------------------------------------------
    # AÑADIR A COLA
    #
    # Pasamos received_at para que audio.py mida todo desde
    # el momento en que Discord entregó el mensaje.
    # --------------------------------------------------------

    add_to_queue(
        guild_id=guild_id,
        user_id=user_id,
        text=text,
        voice_id=voice_id,
        started_at=received_at,
    )

    queued_at = time.perf_counter()

    print(
        "[TTS PERF] "
        "Discord -> cola: "
        f"{(queued_at - received_at) * 1000:.0f} ms"
    )

    print(
        "[TTS] En cola: "
        f"{message.author} "
        f"[{voice_id}] "
        f"{text}"
    )


# ============================================================
# /tts iniciar
# ============================================================

@tts_group.command(
    name="iniciar",
    description=(
        "Lee automáticamente tus mensajes."
    ),
)
async def tts_iniciar(
    interaction: discord.Interaction,
):
    await interaction.response.defer(
        ephemeral=True
    )

    if not interaction.guild:
        await interaction.followup.send(
            "Este comando solo puede "
            "usarse dentro de un servidor.",
            ephemeral=True,
        )

        return

    try:
        voice_client = (
            await get_voice_client(
                interaction
            )
        )

    except Exception as exc:
        print(
            "Error conectando "
            f"a voz: {exc}"
        )

        await interaction.followup.send(
            "❌ No pude conectarme "
            "al canal de voz.",
            ephemeral=True,
        )

        return

    if voice_client is None:
        await interaction.followup.send(
            "Primero entra a un "
            "canal de voz.",
            ephemeral=True,
        )

        return

    guild_id = (
        interaction.guild.id
    )

    user_id = (
        interaction.user.id
    )

    if is_user_active(
        guild_id,
        user_id,
    ):
        await interaction.followup.send(
            "🔊 Ya tienes el TTS activado.",
            ephemeral=True,
        )

        return

    activate_user(
        guild_id,
        user_id,
    )

    cancel_idle_disconnect(
        guild_id
    )

    ensure_guild_worker(
        bot,
        guild_id,
    )

    await update_presence(
        bot
    )

    await interaction.followup.send(
        "🔊 TTS activado.",
        ephemeral=True,
    )


# ============================================================
# /tts detener
# ============================================================

@tts_group.command(
    name="detener",
    description=(
        "Deja de leer automáticamente "
        "tus mensajes."
    ),
)
async def tts_detener(
    interaction: discord.Interaction,
):
    if not interaction.guild:
        await interaction.response.send_message(
            "Este comando solo puede "
            "usarse dentro de un servidor.",
            ephemeral=True,
        )

        return

    # Respondemos a Discord inmediatamente para evitar
    # "La aplicación no ha respondido".
    await interaction.response.defer(
        ephemeral=True
    )

    guild_id = (
        interaction.guild.id
    )

    user_id = (
        interaction.user.id
    )

    if not is_user_active(
        guild_id,
        user_id,
    ):
        await interaction.followup.send(
            "No tienes el TTS activado.",
            ephemeral=True,
        )

        return

    # Deja de aceptar futuros mensajes automáticos.
    deactivate_user(
        guild_id,
        user_id,
    )

    # Elimina TODOS sus mensajes que todavía estén
    # esperando en la cola.
    removed_count = (
        remove_all_user_items(
            guild_id,
            user_id,
        )
    )

    # --------------------------------------------------------
    # DETENER MENSAJE ACTUAL
    # --------------------------------------------------------

    current = (
        guild_current_items.get(
            guild_id
        )
    )

    voice_client = (
        interaction.guild.voice_client
    )

    stopped_current = False

    if (
        current is not None
        and current.get(
            "user_id"
        )
        == user_id
    ):
        guild_cancelled_items[
            guild_id
        ].add(
            current["id"]
        )

        if (
            voice_client
            and voice_client.is_playing()
        ):
            voice_client.stop()

            stopped_current = True

    await update_presence(
        bot
    )

    if (
        get_guild_active_count(
            guild_id
        )
        == 0
    ):
        schedule_idle_disconnect(
            bot,
            guild_id,
        )

    print(
        "[TTS] Usuario detenido: "
        f"{user_id} | "
        f"actual={stopped_current} | "
        f"cola_eliminada={removed_count}"
    )

    await interaction.followup.send(
        "⏹ TTS desactivado y "
        "tus mensajes pendientes fueron detenidos.",
        ephemeral=True,
    )


# ============================================================
# /tts decir
# ============================================================

@tts_group.command(
    name="decir",
    description=(
        "Reproduce texto o lee "
        "el texto de una imagen."
    ),
)
@app_commands.describe(
    texto=(
        "Texto que quieres reproducir"
    ),
    imagen=(
        "Imagen cuyo texto quieres leer"
    ),
)
async def tts_decir(
    interaction: discord.Interaction,
    texto: str | None = None,
    imagen: discord.Attachment | None = None,
):
    command_started_at = (
        time.perf_counter()
    )

    await interaction.response.defer()

    if not interaction.guild:
        await interaction.followup.send(
            "❌ Este comando solo puede "
            "usarse dentro de un servidor."
        )

        return

    if texto:
        texto = normalize_spaces(
            texto
        )

    if (
        not texto
        and imagen is None
    ):
        await interaction.followup.send(
            "❌ Debes escribir texto "
            "o adjuntar una imagen."
        )

        return

    if (
        imagen is not None
        and not is_supported_image(
            imagen
        )
    ):
        await interaction.followup.send(
            "❌ El archivo adjunto "
            "no es una imagen compatible."
        )

        return

    # --------------------------------------------------------
    # CONECTAR A VOZ
    # --------------------------------------------------------

    try:
        voice_client = (
            await get_voice_client(
                interaction
            )
        )

    except Exception as exc:
        print(
            "Error conectando "
            f"a voz: {exc}"
        )

        await interaction.followup.send(
            "❌ No pude conectarme "
            "al canal de voz."
        )

        return

    if voice_client is None:
        await interaction.followup.send(
            "Primero entra a un "
            "canal de voz."
        )

        return

    display_name = (
        interaction.user.display_name
        if isinstance(
            interaction.user,
            discord.Member,
        )
        else interaction.user.name
    )

    spoken_parts = []

    if texto:
        spoken_parts.append(
            texto
        )

    ocr_text = ""

    # --------------------------------------------------------
    # OCR
    # --------------------------------------------------------

    if imagen is not None:
        print(
            "[TTS DECIR] "
            "Procesando imagen con OCR..."
        )

        try:
            ocr_text = (
                await get_attachment_ocr_text(
                    imagen
                )
            )

        except Exception as exc:
            print(
                "[TTS DECIR] "
                "Error procesando OCR: "
                f"{exc}"
            )

            ocr_text = ""

        if ocr_text:
            spoken_parts.append(
                ocr_text
            )

    final_text = normalize_spaces(
        ". ".join(
            spoken_parts
        )
    )

    if not final_text:
        if imagen is not None:
            try:
                image_file = (
                    await imagen.to_file()
                )

                await interaction.followup.send(
                    content=(
                        f"**{display_name}:** "
                        "*(no se detectó texto)*"
                    ),
                    file=image_file,
                )

            except Exception as exc:
                print(
                    "[TTS DECIR] "
                    "Error enviando imagen: "
                    f"{exc}"
                )

                await interaction.followup.send(
                    "❌ No pude detectar texto "
                    "en la imagen."
                )

            return

        await interaction.followup.send(
            "❌ No hay nada que reproducir."
        )

        return

    # --------------------------------------------------------
    # AÑADIR A COLA
    # --------------------------------------------------------

    guild_id = (
        interaction.guild.id
    )

    user_id = (
        interaction.user.id
    )

    voice_id = get_user_voice(
        user_id,
        VOICES,
    )

    ensure_guild_worker(
        bot,
        guild_id,
    )

    add_to_queue(
        guild_id=guild_id,
        user_id=user_id,
        text=final_text,
        voice_id=voice_id,
        started_at=command_started_at,
    )

    if (
        get_guild_active_count(
            guild_id
        )
        == 0
    ):
        schedule_idle_disconnect(
            bot,
            guild_id,
        )

    # --------------------------------------------------------
    # RESPUESTA PÚBLICA
    # --------------------------------------------------------

    if imagen is not None:
        try:
            image_file = (
                await imagen.to_file()
            )

            if texto:
                await interaction.followup.send(
                    content=(
                        f"**{display_name}:** "
                        f"{texto}"
                    ),
                    file=image_file,
                )

            else:
                await interaction.followup.send(
                    content=(
                        f"**{display_name}:**"
                    ),
                    file=image_file,
                )

        except Exception as exc:
            print(
                "[TTS DECIR] "
                "Error enviando imagen: "
                f"{exc}"
            )

            await interaction.followup.send(
                f"**{display_name}:** "
                "🖼️ imagen procesada"
            )

        return

    await interaction.followup.send(
        f"**{display_name}:** "
        f"{final_text}"
    )


# ============================================================
# /tts saltar
# ============================================================

@tts_group.command(
    name="saltar",
    description=(
        "Salta tu mensaje actual "
        "o tu próximo mensaje en cola."
    ),
)
async def tts_saltar(
    interaction: discord.Interaction,
):
    if not interaction.guild:
        await interaction.response.send_message(
            "Este comando solo puede "
            "usarse dentro de un servidor.",
            ephemeral=True,
        )

        return

    # ACK inmediato a Discord.
    await interaction.response.defer(
        ephemeral=True
    )

    guild_id = (
        interaction.guild.id
    )

    user_id = (
        interaction.user.id
    )

    ensure_guild_state(
        guild_id
    )

    current = (
        guild_current_items.get(
            guild_id
        )
    )

    voice_client = (
        interaction.guild.voice_client
    )

    # --------------------------------------------------------
    # ACTUAL
    # --------------------------------------------------------

    if (
        current is not None
        and current.get(
            "user_id"
        )
        == user_id
    ):
        guild_cancelled_items[
            guild_id
        ].add(
            current["id"]
        )

        if (
            voice_client
            and voice_client.is_playing()
        ):
            voice_client.stop()

        await interaction.followup.send(
            "⏭ Saltaste tu mensaje actual.",
            ephemeral=True,
        )

        return

    # --------------------------------------------------------
    # SIGUIENTE EN COLA
    # --------------------------------------------------------

    removed = (
        remove_next_user_item(
            guild_id,
            user_id,
        )
    )

    if removed:
        await interaction.followup.send(
            "⏭ Saltaste tu próximo "
            "mensaje en cola.",
            ephemeral=True,
        )

        return

    await interaction.followup.send(
        "No tienes ningún mensaje "
        "que pueda saltar.",
        ephemeral=True,
    )


# ============================================================
# /voz actual
# ============================================================

@voz_group.command(
    name="actual",
    description=(
        "Muestra tu voz TTS actual."
    ),
)
async def voz_actual(
    interaction: discord.Interaction,
):
    user_id = (
        interaction.user.id
    )

    voice_id = get_user_voice(
        user_id,
        VOICES,
    )

    label = get_voice_label(
        voice_id
    )

    await interaction.response.send_message(
        f"🔊 Tu voz actual es "
        f"**{label}**.",
        ephemeral=True,
    )


# ============================================================
# NAVEGADOR DE VOCES
# ============================================================

async def send_voice_browser(
    interaction,
    gender,
):
    view = None

    try:
        signature = inspect.signature(
            VoiceBrowserView
        )

        kwargs = {}

        parameter_names = set(
            signature.parameters.keys()
        )

        if "user_id" in parameter_names:
            kwargs["user_id"] = (
                interaction.user.id
            )

        if "owner_id" in parameter_names:
            kwargs["owner_id"] = (
                interaction.user.id
            )

        if "gender" in parameter_names:
            kwargs["gender"] = gender

        if "interaction" in parameter_names:
            kwargs["interaction"] = (
                interaction
            )

        view = VoiceBrowserView(
            **kwargs
        )

    except Exception:
        view = None

    if view is None:
        attempts = (
            (
                interaction.user.id,
                gender,
            ),
            (
                gender,
                interaction.user.id,
            ),
            (
                gender,
            ),
            (),
        )

        for args in attempts:
            try:
                view = VoiceBrowserView(
                    *args
                )

                break

            except TypeError:
                continue

    if view is None:
        await interaction.response.send_message(
            "❌ No pude abrir "
            "el selector de voces.",
            ephemeral=True,
        )

        return

    for method_name in (
        "send_initial_message",
        "send_initial",
        "send",
    ):
        method = getattr(
            view,
            method_name,
            None,
        )

        if (
            method is not None
            and callable(method)
        ):
            try:
                result = method(
                    interaction
                )

                if inspect.isawaitable(
                    result
                ):
                    await result

                return

            except TypeError:
                pass

    title = (
        "Voces masculinas"
        if gender == "male"
        else "Voces femeninas"
    )

    await interaction.response.send_message(
        f"🔊 **{title}**",
        view=view,
        ephemeral=True,
    )


# ============================================================
# /voces hombres
# ============================================================

@voces_group.command(
    name="hombres",
    description=(
        "Explora las voces masculinas."
    ),
)
async def voces_hombres(
    interaction: discord.Interaction,
):
    await send_voice_browser(
        interaction,
        "male",
    )


# ============================================================
# /voces mujeres
# ============================================================

@voces_group.command(
    name="mujeres",
    description=(
        "Explora las voces femeninas."
    ),
)
async def voces_mujeres(
    interaction: discord.Interaction,
):
    await send_voice_browser(
        interaction,
        "female",
    )


# ============================================================
# /apodo poner
# ============================================================

@apodo_group.command(
    name="poner",
    description=(
        "Elige el nombre que PenguSpeak "
        "usará para referirse a ti."
    ),
)
@app_commands.describe(
    nombre="Tu apodo para el TTS"
)
async def apodo_poner(
    interaction: discord.Interaction,
    nombre: str,
):
    nombre = normalize_spaces(
        nombre
    )

    if not nombre:
        await interaction.response.send_message(
            "❌ El apodo está vacío.",
            ephemeral=True,
        )

        return

    if len(nombre) > 30:
        await interaction.response.send_message(
            "❌ El apodo no puede tener "
            "más de 30 caracteres.",
            ephemeral=True,
        )

        return

    if not is_valid_nickname(
        nombre
    ):
        await interaction.response.send_message(
            "❌ El apodo solo puede contener "
            "letras, números y espacios.",
            ephemeral=True,
        )

        return

    set_nickname(
        interaction.user.id,
        nombre,
    )

    await interaction.response.send_message(
        f"✅ Tu apodo ahora es "
        f"**{nombre}**.",
        ephemeral=True,
    )


# ============================================================
# /apodo quitar
# ============================================================

@apodo_group.command(
    name="quitar",
    description=(
        "Elimina tu apodo personalizado."
    ),
)
async def apodo_quitar(
    interaction: discord.Interaction,
):
    nickname = get_nickname(
        interaction.user.id
    )

    if not nickname:
        await interaction.response.send_message(
            "No tienes ningún "
            "apodo configurado.",
            ephemeral=True,
        )

        return

    remove_nickname(
        interaction.user.id
    )

    await interaction.response.send_message(
        "✅ Apodo eliminado.",
        ephemeral=True,
    )


# ============================================================
# /apodo actual
# ============================================================

@apodo_group.command(
    name="actual",
    description=(
        "Muestra tu apodo actual."
    ),
)
async def apodo_actual(
    interaction: discord.Interaction,
):
    nickname = get_nickname(
        interaction.user.id
    )

    if nickname:
        await interaction.response.send_message(
            f"Tu apodo actual es "
            f"**{nickname}**.",
            ephemeral=True,
        )

        return

    await interaction.response.send_message(
        "No tienes un apodo personalizado.",
        ephemeral=True,
    )


# ============================================================
# REGISTRAR GRUPOS
# ============================================================

bot.tree.add_command(
    tts_group
)

bot.tree.add_command(
    voz_group
)

bot.tree.add_command(
    voces_group
)

bot.tree.add_command(
    apodo_group
)


# ============================================================
# EJECUTAR
# ============================================================

bot.run(
    DISCORD_TOKEN
)