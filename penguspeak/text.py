import re
import unicodedata

import discord

from penguspeak.database import (
    get_nickname,
)

from penguspeak.ocr import (
    get_message_ocr_text,
    is_supported_image,
)

from penguspeak.state import (
    should_announce_name,
)


# ============================================================
# UTILIDADES
# ============================================================

def normalize_spaces(
    text,
):
    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


# ============================================================
# VALIDACIÓN DE APODOS
# ============================================================

def is_valid_nickname(
    text,
):
    """
    Permite únicamente:
    - Letras
    - Números
    - Espacios

    No permite:
    - Emojis
    - Símbolos
    - Menciones
    - Puntuación
    """

    if not text:
        return False

    for character in text:
        if character.isspace():
            continue

        category = (
            unicodedata.category(
                character
            )
        )

        if (
            not category.startswith(
                "L"
            )
            and not category.startswith(
                "N"
            )
        ):
            return False

    return True


# ============================================================
# LIMPIEZA DE NOMBRES
# ============================================================

def clean_discord_name(
    name,
):
    """
    Elimina emojis y símbolos del nombre.

    Ejemplo:

        🌸 Heather 🎮
             ↓
        Heather
    """

    cleaned = []

    for character in name:
        if character.isspace():
            cleaned.append(
                " "
            )

            continue

        category = (
            unicodedata.category(
                character
            )
        )

        if (
            category.startswith(
                "L"
            )
            or category.startswith(
                "N"
            )
        ):
            cleaned.append(
                character
            )

    result = normalize_spaces(
        "".join(
            cleaned
        )
    )

    if not result:
        return "Usuario"

    return result


def get_spoken_name(
    member,
):
    nickname = get_nickname(
        member.id
    )

    if nickname:
        return nickname

    if isinstance(
        member,
        discord.Member,
    ):
        return clean_discord_name(
            member.display_name
        )

    return clean_discord_name(
        member.name
    )


# ============================================================
# URLs
# ============================================================

URL_PATTERN = re.compile(
    r"https?://\S+|www\.\S+",
    re.IGNORECASE,
)


def replace_urls(
    text,
):
    return URL_PATTERN.sub(
        " envió un enlace ",
        text,
    )


# ============================================================
# EMOJIS PERSONALIZADOS
# ============================================================

CUSTOM_EMOJI_PATTERN = re.compile(
    r"<a?:[A-Za-z0-9_]+:\d+>"
)


def remove_custom_emojis(
    text,
):
    return CUSTOM_EMOJI_PATTERN.sub(
        " ",
        text,
    )


# ============================================================
# EMOJIS UNICODE
# ============================================================

def remove_unicode_emojis(
    text,
):
    result = []

    for character in text:
        category = (
            unicodedata.category(
                character
            )
        )

        # Símbolos Unicode.
        if category.startswith(
            "S"
        ):
            continue

        # Componentes invisibles usados
        # frecuentemente en emojis.
        if category in {
            "Cf",
            "Cs",
        }:
            continue

        result.append(
            character
        )

    return "".join(
        result
    )


# ============================================================
# MENCIONES DE USUARIOS
# ============================================================

def replace_user_mentions(
    text,
    message,
):
    for member in message.mentions:
        name = get_spoken_name(
            member
        )

        text = text.replace(
            f"<@{member.id}>",
            f" mencionó a {name} ",
        )

        text = text.replace(
            f"<@!{member.id}>",
            f" mencionó a {name} ",
        )

    return text


# ============================================================
# CANALES
# ============================================================

def replace_channel_mentions(
    text,
    message,
):
    for channel in (
        message.channel_mentions
    ):
        channel_name = (
            clean_discord_name(
                channel.name
            )
        )

        text = text.replace(
            f"<#{channel.id}>",
            f" canal {channel_name} ",
        )

    return text


# ============================================================
# ROLES
# ============================================================

def replace_role_mentions(
    text,
    message,
):
    for role in (
        message.role_mentions
    ):
        role_name = (
            clean_discord_name(
                role.name
            )
        )

        text = text.replace(
            f"<@&{role.id}>",
            (
                " mencionó al rol "
                f"{role_name} "
            ),
        )

    return text


# ============================================================
# ARCHIVOS
# ============================================================

def get_regular_attachment_text(
    message,
):
    """
    GIF:
        ignorado.

    Imagen:
        la procesa OCR.

    Otros archivos:
        "envió un archivo".
    """

    parts = []

    for attachment in (
        message.attachments
    ):
        filename = (
            attachment.filename
            or ""
        ).lower()

        content_type = (
            attachment.content_type
            or ""
        ).lower()

        # GIF ignorado completamente.
        if (
            filename.endswith(
                ".gif"
            )
            or content_type
            == "image/gif"
        ):
            continue

        # Las imágenes pertenecen al OCR.
        if is_supported_image(
            attachment
        ):
            continue

        parts.append(
            "envió un archivo"
        )

    return parts


# ============================================================
# LIMPIEZA DEL MENSAJE
# ============================================================

def clean_message_text(
    message,
):
    text = (
        message.content
        or ""
    )

    # Primero las construcciones propias
    # de Discord.
    text = replace_user_mentions(
        text,
        message,
    )

    text = replace_channel_mentions(
        text,
        message,
    )

    text = replace_role_mentions(
        text,
        message,
    )

    # Enlaces.
    text = replace_urls(
        text
    )

    # Emojis.
    text = remove_custom_emojis(
        text
    )

    text = remove_unicode_emojis(
        text
    )

    text = normalize_spaces(
        text
    )

    # Archivos normales.
    attachments = (
        get_regular_attachment_text(
            message
        )
    )

    if attachments:
        extra = ". ".join(
            attachments
        )

        if text:
            text = (
                f"{text}. {extra}"
            )

        else:
            text = extra

    return normalize_spaces(
        text
    )


# ============================================================
# REPLIES
# ============================================================

async def get_reply_target_name(
    message,
):
    if not message.reference:
        return None

    resolved = (
        message.reference.resolved
    )

    if isinstance(
        resolved,
        discord.Message,
    ):
        return get_spoken_name(
            resolved.author
        )

    message_id = (
        message.reference.message_id
    )

    if not message_id:
        return None

    try:
        replied_message = (
            await message.channel.fetch_message(
                message_id
            )
        )

        return get_spoken_name(
            replied_message.author
        )

    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException,
    ):
        return None


# ============================================================
# CONSTRUIR MENSAJE FINAL
# ============================================================

async def build_spoken_message(
    message,
):
    """
    Combina:

    - Nombre del usuario.
    - Reply.
    - Texto normal.
    - OCR de imágenes.
    """

    normal_text = (
        clean_message_text(
            message
        )
    )

    # OCR solo se ejecuta aquí.
    #
    # Como build_spoken_message solamente se llama
    # para usuarios con /tts iniciar activo,
    # las imágenes de usuarios inactivos no gastan
    # procesamiento.
    ocr_results = (
        await get_message_ocr_text(
            message
        )
    )

    content_parts = []

    if normal_text:
        content_parts.append(
            normal_text
        )

    for ocr_text in ocr_results:
        content_parts.append(
            "Texto de la imagen: "
            f"{ocr_text}"
        )

    # GIF solo, emoji solo, o imagen sin
    # texto detectable.
    if not content_parts:
        return None

    content = ". ".join(
        content_parts
    )

    author_name = (
        get_spoken_name(
            message.author
        )
    )

    reply_name = (
        await get_reply_target_name(
            message
        )
    )

    parts = []

    if should_announce_name(
        message.guild.id,
        message.author.id,
    ):
        parts.append(
            f"{author_name} dice:"
        )

    if reply_name:
        parts.append(
            "Respondiendo a "
            f"{reply_name}:"
        )

    parts.append(
        content
    )

    return " ".join(
        parts
    )
