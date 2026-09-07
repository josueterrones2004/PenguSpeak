import discord

from discord import app_commands
from discord.ext import commands

from config import DISCORD_TOKEN

from penguspeak.database import (
    init_database,
    get_user_voice,
    get_nickname,
    set_nickname,
    remove_nickname,
)

from penguspeak.queue import (
    add_to_queue,
    remove_next_user_item,
    ensure_guild_worker,
)

from penguspeak.state import (
    activate_user,
    deactivate_user,
    is_user_active,
    get_guild_active_count,
    guild_current_items,
    guild_cancelled_items,
    ensure_guild_state,
    cancel_idle_disconnect,
    schedule_idle_disconnect,
    update_presence,
)

from penguspeak.text import (
    build_spoken_message,
    get_spoken_name,
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
# CONFIGURACIÓN
# ============================================================

intents = discord.Intents.default()

intents.message_content = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
)


# ============================================================
# BASE DE DATOS
# ============================================================

init_database()


# ============================================================
# CONEXIÓN A VOZ
# ============================================================

async def get_voice_client(
    interaction: discord.Interaction,
):
    if not interaction.guild:
        return None

    if not isinstance(
        interaction.user,
        discord.Member,
    ):
        return None

    if (
        not interaction.user.voice
        or not interaction.user.voice.channel
    ):
        return None

    guild_id = (
        interaction.guild.id
    )

    channel = (
        interaction.user.voice.channel
    )

    voice_client = (
        interaction.guild.voice_client
    )

    # Hay actividad nueva.
    # Cancelamos una posible desconexión.
    cancel_idle_disconnect(
        guild_id
    )

    if voice_client is None:
        voice_client = (
            await channel.connect(
		self_deaf=True
        	)
        )

    elif (
        voice_client.channel
        != channel
    ):
        await voice_client.move_to(
            channel
        )

    ensure_guild_worker(
        bot,
        guild_id,
    )

    return voice_client


# ============================================================
# EVENTOS
# ============================================================

@bot.event
async def on_ready():
    print(
        f"PenguSpeak conectado como {bot.user}"
    )

    print(
        f"ID: {bot.user.id}"
    )

    await update_presence(
        bot
    )


# ============================================================
# CAMBIOS EN CANALES DE VOZ
# ============================================================

@bot.event
async def on_voice_state_update(
    member,
    before,
    after,
):
    guild_id = (
        member.guild.id
    )

    if not is_user_active(
        guild_id,
        member.id,
    ):
        return

    voice_client = (
        member.guild.voice_client
    )

    # El usuario sigue en el mismo canal
    # que el bot.
    if (
        after.channel
        and voice_client
        and voice_client.channel
        == after.channel
    ):
        return

    # Salió del canal donde estaba el bot
    # o salió completamente de voz.
    deactivate_user(
        guild_id,
        member.id,
    )

    await update_presence(
        bot
    )

    # Si ya no queda nadie utilizando TTS,
    # empieza el contador de 5 minutos.
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


# ============================================================
# MENSAJES
# ============================================================

@bot.event
async def on_message(
    message,
):
    if message.author.bot:
        return

    if not message.guild:
        return

    guild_id = (
        message.guild.id
    )

    user_id = (
        message.author.id
    )

    if not is_user_active(
        guild_id,
        user_id,
    ):
        return

    if (
        not isinstance(
            message.author,
            discord.Member,
        )
        or not message.author.voice
        or not message.author.voice.channel
    ):
        deactivate_user(
            guild_id,
            user_id,
        )

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

        return

    voice_client = (
        message.guild.voice_client
    )

    if (
        not voice_client
        or not voice_client.is_connected()
    ):
        return

    if (
        voice_client.channel
        != message.author.voice.channel
    ):
        deactivate_user(
            guild_id,
            user_id,
        )

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

        return

    text = await build_spoken_message(
        message
    )

    if not text:
        return

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
        text=text,
        voice_id=voice_id,
    )

    print(
        "[TTS] En cola: "
        f"{message.author} "
        f"[{voice_id}] "
        f"{text}"
    )


# ============================================================
# /tts
# ============================================================

tts_group = app_commands.Group(
    name="tts",
    description=(
        "Controla el sistema "
        "de texto a voz."
    ),
)


# ============================================================
# /tts iniciar
# ============================================================

@tts_group.command(
    name="iniciar",
    description=(
        "Empieza a leer automáticamente "
        "tus mensajes."
    ),
)
async def tts_iniciar(
    interaction: discord.Interaction,
):
    await interaction.response.defer(
        ephemeral=True
    )

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

    activate_user(
        guild_id,
        interaction.user.id,
    )

    cancel_idle_disconnect(
        guild_id
    )

    await update_presence(
        bot
    )

    voice_id = get_user_voice(
        interaction.user.id,
        VOICES,
    )

    await interaction.followup.send(
        "✅ TTS activado.\n"
        f"Voz: **{get_voice_label(voice_id)}**",
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
        await interaction.response.send_message(
            "No tienes el TTS activado.",
            ephemeral=True,
        )

        return

    deactivate_user(
        guild_id,
        user_id,
    )

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

    await interaction.response.send_message(
        "⏹️ TTS desactivado.",
        ephemeral=True,
    )


# ============================================================
# /tts decir
# ============================================================

@tts_group.command(
    name="decir",
    description=(
        "Añade un único mensaje "
        "a la cola de voz."
    ),
)
@app_commands.describe(
    texto="Texto que quieres reproducir"
)
async def tts_decir(
    interaction: discord.Interaction,
    texto: str,
):
    await interaction.response.defer(
        ephemeral=True
    )

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

    texto = normalize_spaces(
        texto
    )

    if not texto:
        await interaction.followup.send(
            "El mensaje está vacío.",
            ephemeral=True,
        )

        return

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
        text=texto,
        voice_id=voice_id,
    )

    # Si nadie tiene el modo continuo activo,
    # el bot se desconectará 5 minutos después
    # de esta actividad.
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

    await interaction.followup.send(
        "🔊 Mensaje añadido a la cola.",
        ephemeral=True,
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

    # El audio actual pertenece
    # al usuario que ejecutó el comando.
    if (
        current
        and current["user_id"]
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

        await interaction.response.send_message(
            "⏭️ Saltaste tu "
            "mensaje actual.",
            ephemeral=True,
        )

        return

    # Si está hablando otra persona,
    # jamás se interrumpe.
    removed = (
        remove_next_user_item(
            guild_id,
            user_id,
        )
    )

    if removed:
        await interaction.response.send_message(
            "⏭️ Eliminé tu próximo "
            "mensaje de la cola.",
            ephemeral=True,
        )

        return

    await interaction.response.send_message(
        "No tienes ningún mensaje "
        "que saltar.",
        ephemeral=True,
    )


# ============================================================
# /voz
# ============================================================

voz_group = app_commands.Group(
    name="voz",
    description=(
        "Consulta tu configuración "
        "de voz."
    ),
)


@voz_group.command(
    name="actual",
    description=(
        "Muestra la voz "
        "que tienes seleccionada."
    ),
)
async def voz_actual(
    interaction: discord.Interaction,
):
    voice_id = get_user_voice(
        interaction.user.id,
        VOICES,
    )

    await interaction.response.send_message(
        "🔊 Tu voz actual es "
        f"**{get_voice_label(voice_id)}**.",
        ephemeral=True,
    )


# ============================================================
# /voces
# ============================================================

voces_group = app_commands.Group(
    name="voces",
    description=(
        "Explora y selecciona "
        "las voces disponibles."
    ),
)


async def mostrar_catalogo(
    interaction: discord.Interaction,
    gender: str,
):
    await interaction.response.defer(
        ephemeral=True
    )

    try:
        view = VoiceBrowserView(
            gender=gender,
            owner_id=interaction.user.id,
        )

        await interaction.followup.send(
            content=view.get_page_content(),
            files=view.get_page_files(),
            view=view,
            ephemeral=True,
        )

    except Exception as exc:
        print(
            "Error mostrando voces: "
            f"{exc}"
        )

        await interaction.followup.send(
            "❌ No pude cargar "
            "las demos.",
            ephemeral=True,
        )


@voces_group.command(
    name="hombres",
    description=(
        "Escucha demos de "
        "voces masculinas."
    ),
)
async def voces_hombres(
    interaction: discord.Interaction,
):
    await mostrar_catalogo(
        interaction,
        "male",
    )


@voces_group.command(
    name="mujeres",
    description=(
        "Escucha demos de "
        "voces femeninas."
    ),
)
async def voces_mujeres(
    interaction: discord.Interaction,
):
    await mostrar_catalogo(
        interaction,
        "female",
    )


# ============================================================
# /apodo
# ============================================================

apodo_group = app_commands.Group(
    name="apodo",
    description=(
        "Configura el apodo que "
        "el bot dirá al leer tus mensajes."
    ),
)


@apodo_group.command(
    name="poner",
    description="Establece tu apodo.",
)
@app_commands.describe(
    nombre="Solo letras, números y espacios"
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
            "El apodo no puede "
            "estar vacío.",
            ephemeral=True,
        )

        return

    if len(nombre) > 30:
        await interaction.response.send_message(
            "El apodo puede tener "
            "como máximo 30 caracteres.",
            ephemeral=True,
        )

        return

    if not is_valid_nickname(
        nombre
    ):
        await interaction.response.send_message(
            "El apodo solo puede contener "
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
            "No tienes un apodo "
            "personalizado.",
            ephemeral=True,
        )

        return

    remove_nickname(
        interaction.user.id
    )

    await interaction.response.send_message(
        "✅ Apodo eliminado. "
        "Se volverá a usar tu "
        "nombre visible de Discord.",
        ephemeral=True,
    )


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

    display_name = (
        get_spoken_name(
            interaction.user
        )
    )

    await interaction.response.send_message(
        "No tienes un apodo "
        "personalizado.\n"
        f"Se está usando "
        f"**{display_name}**.",
        ephemeral=True,
    )


# ============================================================
# REGISTRAR COMANDOS
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
# SINCRONIZACIÓN
# ============================================================

@bot.event
async def setup_hook():
    synced = await bot.tree.sync()

    print(
        f"{len(synced)} grupos "
        "de comandos sincronizados."
    )


# ============================================================
# INICIAR
# ============================================================

bot.run(
    DISCORD_TOKEN
)
