import re
import unicodedata

import discord
import emoji

from penguspeak.database import (
    get_nickname,
)

from penguspeak.ocr import (
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


def format_name_list(
    names,
):
    if not names:
        return ""

    if len(names) == 1:
        return names[0]

    if len(names) == 2:
        return (
            f"{names[0]} "
            f"y {names[1]}"
        )

    return (
        ", ".join(
            names[:-1]
        )
        + f" y {names[-1]}"
    )


# ============================================================
# VALIDACIÓN DE APODOS
# ============================================================

def is_valid_nickname(
    text,
):
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
            not category.startswith("L")
            and not category.startswith("N")
        ):
            return False

    return True


# ============================================================
# LIMPIEZA DE NOMBRES
# ============================================================

def clean_discord_name(
    name,
):
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
            category.startswith("L")
            or category.startswith("N")
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
# URLS
# ============================================================

URL_PATTERN = re.compile(
    r"https?://\S+|www\.\S+",
    re.IGNORECASE,
)


def message_contains_url(
    message,
):
    return bool(
        URL_PATTERN.search(
            message.content
            or ""
        )
    )


def remove_urls(
    text,
):
    return normalize_spaces(
        URL_PATTERN.sub(
            " ",
            text,
        )
    )


# ============================================================
# EMOJIS PERSONALIZADOS DE DISCORD
# ============================================================

CUSTOM_EMOJI_PATTERN = re.compile(
    r"<a?:([A-Za-z0-9_]+):\d+>"
)


def humanize_custom_emoji_name(
    name,
):
    # snake_case
    name = name.replace(
        "_",
        " ",
    )

    # camelCase
    name = re.sub(
        r"(?<=[a-záéíóúñ])"
        r"(?=[A-ZÁÉÍÓÚÑ])",
        " ",
        name,
    )

    return normalize_spaces(
        name
    )


def replace_custom_emojis(
    text,
):
    def repl(
        match,
    ):
        emoji_name = (
            match.group(1)
        )

        spoken_name = (
            humanize_custom_emoji_name(
                emoji_name
            )
        )

        if not spoken_name:
            return " "

        return (
            f" {spoken_name} "
        )

    return CUSTOM_EMOJI_PATTERN.sub(
        repl,
        text,
    )


# ============================================================
# EMOJIS UNICODE
# ============================================================

UNICODE_EMOJI_EASTER_EGGS = {
    "👀": "ojitos void",
}


def humanize_unicode_emoji_name(
    name,
):
    name = name.replace(
        "_",
        " ",
    )

    name = name.replace(
        "-",
        " ",
    )

    return normalize_spaces(
        name
    )


def replace_unicode_emojis(
    text,
):
    if not text:
        return ""

    # --------------------------------------------------------
    # EASTER EGGS
    # --------------------------------------------------------

    for (
        unicode_emoji,
        spoken_text,
    ) in (
        UNICODE_EMOJI_EASTER_EGGS.items()
    ):
        text = text.replace(
            unicode_emoji,
            f" {spoken_text} ",
        )

    # --------------------------------------------------------
    # DEMÁS EMOJIS EN ESPAÑOL
    # --------------------------------------------------------

    text = emoji.demojize(
        text,
        language="es",
        delimiters=(
            "__EMOJI__",
            "__",
        ),
    )

    pattern = re.compile(
        r"__EMOJI__(.*?)__"
    )

    def replace_match(
        match,
    ):
        name = (
            match.group(1)
        )

        name = (
            humanize_unicode_emoji_name(
                name
            )
        )

        if not name:
            return " "

        return (
            f" {name} "
        )

    text = pattern.sub(
        replace_match,
        text,
    )

    # --------------------------------------------------------
    # SÍMBOLOS RESIDUALES
    # --------------------------------------------------------

    result = []

    for character in text:
        category = (
            unicodedata.category(
                character
            )
        )

        if category.startswith(
            "S"
        ):
            continue

        if category in {
            "Cf",
            "Cs",
        }:
            continue

        result.append(
            character
        )

    return normalize_spaces(
        "".join(
            result
        )
    )


# ============================================================
# MENCIONES DE USUARIOS
# ============================================================

def get_mentioned_names(
    message,
):
    names = []

    for member in (
        message.mentions
    ):
        name = get_spoken_name(
            member
        )

        if name not in names:
            names.append(
                name
            )

    return names


def remove_user_mentions(
    text,
    message,
):
    for member in (
        message.mentions
    ):
        text = text.replace(
            f"<@{member.id}>",
            " ",
        )

        text = text.replace(
            f"<@!{member.id}>",
            " ",
        )

    return normalize_spaces(
        text
    )


def replace_user_mentions(
    text,
    message,
):
    for member in (
        message.mentions
    ):
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
            (
                f" canal "
                f"{channel_name} "
            ),
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
# STICKERS
# ============================================================

def get_sticker_text(
    message,
):
    parts = []

    for sticker in (
        message.stickers
    ):
        sticker_name = (
            getattr(
                sticker,
                "name",
                "",
            )
            or ""
        )

        sticker_name = (
            clean_discord_name(
                sticker_name
            )
        )

        if not sticker_name:
            continue

        parts.append(
            (
                "sticker "
                f"{sticker_name}"
            )
        )

    return parts


# ============================================================
# IMÁGENES
# ============================================================

def count_message_images(
    message,
):
    count = 0

    for attachment in (
        message.attachments
    ):
        if is_supported_image(
            attachment
        ):
            count += 1

    return count


# ============================================================
# VIDEOS
# ============================================================

VIDEO_EXTENSIONS = (
    ".mp4",
    ".mov",
    ".webm",
    ".mkv",
    ".avi",
    ".m4v",
)


def is_video_attachment(
    attachment,
):
    filename = (
        attachment.filename
        or ""
    ).lower()

    content_type = (
        attachment.content_type
        or ""
    ).lower()

    if content_type.startswith(
        "video/"
    ):
        return True

    return filename.endswith(
        VIDEO_EXTENSIONS
    )


def count_message_videos(
    message,
):
    count = 0

    for attachment in (
        message.attachments
    ):
        if is_video_attachment(
            attachment
        ):
            count += 1

    return count


# ============================================================
# ARCHIVOS NORMALES
# ============================================================

def get_regular_attachment_text(
    message,
):
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

        # GIF ignorado.
        if (
            filename.endswith(
                ".gif"
            )
            or content_type
            == "image/gif"
        ):
            continue

        # Imágenes procesadas aparte.
        if is_supported_image(
            attachment
        ):
            continue

        # Videos procesados aparte.
        if is_video_attachment(
            attachment
        ):
            continue

        parts.append(
            "envió un archivo"
        )

    return parts


# ============================================================
# LIMPIEZA DE TEXTO
# ============================================================

def process_message_text(
    text,
    message,
    *,
    include_user_mentions=True,
):
    if include_user_mentions:
        text = replace_user_mentions(
            text,
            message,
        )

    else:
        text = remove_user_mentions(
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

    text = replace_custom_emojis(
        text
    )

    text = replace_unicode_emojis(
        text
    )

    return normalize_spaces(
        text
    )


def clean_message_text(
    message,
):
    text = (
        message.content
        or ""
    )

    text = process_message_text(
        text,
        message,
    )

    # --------------------------------------------------------
    # STICKERS
    # --------------------------------------------------------

    stickers = (
        get_sticker_text(
            message
        )
    )

    if stickers:
        sticker_text = ". ".join(
            stickers
        )

        if text:
            text = (
                f"{text}. "
                f"{sticker_text}"
            )

        else:
            text = (
                sticker_text
            )

    # --------------------------------------------------------
    # OTROS ARCHIVOS
    # --------------------------------------------------------

    attachments = (
        get_regular_attachment_text(
            message
        )
    )

    if attachments:
        attachment_text = (
            ". ".join(
                attachments
            )
        )

        if text:
            text = (
                f"{text}. "
                f"{attachment_text}"
            )

        else:
            text = (
                attachment_text
            )

    return normalize_spaces(
        text
    )


# ============================================================
# TEXTO ACOMPAÑANDO MULTIMEDIA
# ============================================================

def get_media_caption(
    message,
):
    """
    Obtiene únicamente lo que escribió el usuario
    junto a una imagen/video/enlace.

    Las menciones de usuarios se eliminan porque,
    para multimedia, se expresan como:

    "etiquetó a X en una imagen"

    en vez de repetir:

    "mencionó a X".
    """

    text = (
        message.content
        or ""
    )

    text = remove_urls(
        text
    )

    text = process_message_text(
        text,
        message,
        include_user_mentions=False,
    )

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
# FRASES DE MULTIMEDIA
# ============================================================

def build_image_phrase(
    author_name,
    image_count,
    mentioned_names,
):
    if mentioned_names:
        targets = format_name_list(
            mentioned_names
        )

        if image_count == 1:
            return (
                f"{author_name} "
                f"etiquetó a {targets} "
                "en una imagen"
            )

        return (
            f"{author_name} "
            f"etiquetó a {targets} "
            f"en {image_count} imágenes"
        )

    if image_count == 1:
        return (
            f"{author_name} "
            "envió una imagen"
        )

    return (
        f"{author_name} "
        f"envió {image_count} imágenes"
    )


def build_video_phrase(
    author_name,
    video_count,
    mentioned_names,
):
    if mentioned_names:
        targets = format_name_list(
            mentioned_names
        )

        if video_count == 1:
            return (
                f"{author_name} "
                f"etiquetó a {targets} "
                "en un video"
            )

        return (
            f"{author_name} "
            f"etiquetó a {targets} "
            f"en {video_count} videos"
        )

    if video_count == 1:
        return (
            f"{author_name} "
            "envió un video"
        )

    return (
        f"{author_name} "
        f"envió {video_count} videos"
    )


# ============================================================
# CONSTRUIR MENSAJE FINAL
#
# IMPORTANTE:
#
# ESTA FUNCIÓN NO HACE OCR.
#
# OCR solo se usa explícitamente mediante:
#
# /tts decir imagen:[archivo]
# ============================================================

async def build_spoken_message(
    message,
):
    author_name = (
        get_spoken_name(
            message.author
        )
    )

    mentioned_names = (
        get_mentioned_names(
            message
        )
    )

    image_count = (
        count_message_images(
            message
        )
    )

    video_count = (
        count_message_videos(
            message
        )
    )

    has_link = (
        message_contains_url(
            message
        )
    )

    caption = (
        get_media_caption(
            message
        )
    )

    # ========================================================
    # IMAGEN
    # ========================================================

    if image_count > 0:
        phrase = build_image_phrase(
            author_name,
            image_count,
            mentioned_names,
        )

        if caption:
            return (
                f"{phrase} "
                f"y dice: {caption}"
            )

        return phrase

    # ========================================================
    # VIDEO
    # ========================================================

    if video_count > 0:
        phrase = build_video_phrase(
            author_name,
            video_count,
            mentioned_names,
        )

        if caption:
            return (
                f"{phrase} "
                f"y dice: {caption}"
            )

        return phrase

    # ========================================================
    # ENLACE
    # ========================================================

    if has_link:
        phrase = (
            f"{author_name} "
            "envió un enlace"
        )

        if caption:
            return (
                f"{phrase} "
                f"y dice: {caption}"
            )

        return phrase

    # ========================================================
    # TEXTO NORMAL
    # ========================================================

    normal_text = (
        clean_message_text(
            message
        )
    )

    reply_name = (
        await get_reply_target_name(
            message
        )
    )

    if not normal_text:
        return None

    # --------------------------------------------------------
    # REPLY
    # --------------------------------------------------------

    if reply_name:
        return (
            f"{author_name} "
            f"responde a {reply_name}: "
            f"{normal_text}"
        )

    # --------------------------------------------------------
    # MENSAJE NORMAL
    # --------------------------------------------------------

    if should_announce_name(
        message.guild.id,
        message.author.id,
    ):
        return (
            f"{author_name} dice: "
            f"{normal_text}"
        )

    return normal_text
