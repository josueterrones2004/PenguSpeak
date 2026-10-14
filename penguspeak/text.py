import re
import unicodedata

import discord
import emoji

from penguspeak.database import get_nickname
def is_supported_image(attachment):
    filename = (attachment.filename or "").lower()
    content_type = (attachment.content_type or "").lower()
    return content_type.startswith("image/") or filename.endswith(
        (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
    )
from penguspeak.state import should_announce_name


URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
CUSTOM_EMOJI_PATTERN = re.compile(r"<a?:([A-Za-z0-9_]+):\d+>")
UNICODE_EMOJI_EASTER_EGGS = {"👀": "ojitos void"}
MENTION_PATTERN = re.compile(r"<@!?\d+>|<@&\d+>|@(?:everyone|here)\b")
VIDEO_EXTENSIONS = (".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v")


def normalize_spaces(text):
    return re.sub(r"\s+", " ", text).strip()


def format_name_list(names):
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} y {names[1]}"
    return ", ".join(names[:-1]) + f" y {names[-1]}"


def is_valid_nickname(text):
    if not text:
        return False
    return all(
        character.isspace()
        or unicodedata.category(character).startswith(("L", "N"))
        for character in text
    )


def clean_discord_name(name):
    cleaned = "".join(
        character if character.isspace() or unicodedata.category(character).startswith(("L", "N")) else ""
        for character in name
    )
    return normalize_spaces(cleaned) or "Usuario"


def get_spoken_name(member):
    nickname = get_nickname(member.id)
    if nickname:
        return nickname
    if isinstance(member, discord.Member):
        return clean_discord_name(member.display_name)
    return clean_discord_name(member.name)


def message_contains_url(message):
    return bool(URL_PATTERN.search(message.content or ""))


def remove_urls(text):
    return normalize_spaces(URL_PATTERN.sub(" ", text))


def humanize_custom_emoji_name(name):
    name = name.replace("_", " ")
    return normalize_spaces(re.sub(r"(?<=[a-záéíóúñ])(?=[A-ZÁÉÍÓÚÑ])", " ", name))


def replace_custom_emojis(text):
    return CUSTOM_EMOJI_PATTERN.sub(
        lambda match: f" {humanize_custom_emoji_name(match.group(1))} ", text
    )


def humanize_unicode_emoji_name(name):
    return normalize_spaces(name.replace("_", " ").replace("-", " "))


def replace_unicode_emojis(text):
    if not text:
        return ""
    for character, spoken in UNICODE_EMOJI_EASTER_EGGS.items():
        text = text.replace(character, f" {spoken} ")
    text = emoji.demojize(text, language="es", delimiters=("__EMOJI__", "__"))
    text = re.sub(
        r"__EMOJI__(.*?)__",
        lambda match: f" {humanize_unicode_emoji_name(match.group(1))} ",
        text,
    )
    return normalize_spaces("".join(
        character for character in text
        if not unicodedata.category(character).startswith("S")
        and unicodedata.category(character) not in {"Cf", "Cs"}
    ))


def get_mention_targets(message):
    """Return ordered, unique targets found in actual message content.

    Member/role IDs prevent conflating people or roles with identical names.
    @everyone/@here count only when Discord marks the message as a real
    everyone/here mention.
    """
    members = {member.id: member for member in message.mentions}
    roles = {role.id: role for role in message.role_mentions}
    everyone_enabled = bool(getattr(message, "mention_everyone", False))
    targets = []
    seen = set()

    for match in MENTION_PATTERN.finditer(message.content or ""):
        token = match.group()
        if token in {"@everyone", "@here"}:
            key = ("everyone",)
            if not everyone_enabled or key in seen:
                continue
            label = "a todos"
        elif token.startswith("<@&"):
            role_id = int(token[3:-1])
            role = roles.get(role_id)
            key = ("role", role_id)
            if role is None or key in seen:
                continue
            label = f"al rol {clean_discord_name(role.name)}"
        else:
            member_id = int(token[3:-1] if token.startswith("<@!") else token[2:-1])
            member = members.get(member_id)
            key = ("user", member_id)
            if member is None or key in seen:
                continue
            label = f"a {get_spoken_name(member)}"
        seen.add(key)
        targets.append(label)
    return targets


def get_mentioned_names(message):
    return [get_spoken_name(member) for member in message.mentions]


def get_mentioned_roles(message):
    return [clean_discord_name(role.name) for role in message.role_mentions]


def has_everyone_mention(message):
    return any(target == "a todos" for target in get_mention_targets(message))


def remove_user_mentions(text, message):
    for member in message.mentions:
        text = text.replace(f"<@{member.id}>", " ")
        text = text.replace(f"<@!{member.id}>", " ")
    return normalize_spaces(text)


def replace_user_mentions(text, message):
    for member in message.mentions:
        name = get_spoken_name(member)
        text = text.replace(f"<@{member.id}>", f" mencionó a {name} ")
        text = text.replace(f"<@!{member.id}>", f" mencionó a {name} ")
    return text


def remove_role_mentions(text, message):
    for role in message.role_mentions:
        text = text.replace(f"<@&{role.id}>", " ")
    return normalize_spaces(text)


def replace_role_mentions(text, message):
    for role in message.role_mentions:
        text = text.replace(f"<@&{role.id}>", f" mencionó al rol {clean_discord_name(role.name)} ")
    return text


def remove_everyone_mentions(text, message=None):
    if message is not None and not getattr(message, "mention_everyone", False):
        return text
    return re.sub(r"@(?:everyone|here)\b", " ", text)


def replace_channel_mentions(text, message):
    for channel in message.channel_mentions:
        text = text.replace(f"<#{channel.id}>", f" canal {clean_discord_name(channel.name)} ")
    return text


def get_sticker_text(message):
    return [f"sticker {clean_discord_name(sticker.name)}" for sticker in message.stickers if getattr(sticker, "name", None)]


def count_message_images(message):
    return sum(1 for attachment in message.attachments if is_supported_image(attachment))


def is_video_attachment(attachment):
    filename = (attachment.filename or "").lower()
    content_type = (attachment.content_type or "").lower()
    return content_type.startswith("video/") or filename.endswith(VIDEO_EXTENSIONS)


def count_message_videos(message):
    return sum(1 for attachment in message.attachments if is_video_attachment(attachment))


def get_regular_attachment_text(message):
    parts = []
    for attachment in message.attachments:
        filename = (attachment.filename or "").lower()
        content_type = (attachment.content_type or "").lower()
        if filename.endswith(".gif") or content_type == "image/gif":
            continue
        if is_supported_image(attachment) or is_video_attachment(attachment):
            continue
        parts.append("envió un archivo")
    return parts


def process_message_text(
    text,
    message,
    *,
    include_user_mentions=True,
    include_role_mentions=True,
    include_everyone_mentions=True,
):
    text = (
        replace_user_mentions(text, message)
        if include_user_mentions else remove_user_mentions(text, message)
    )
    text = replace_channel_mentions(text, message)
    text = (
        replace_role_mentions(text, message)
        if include_role_mentions else remove_role_mentions(text, message)
    )
    if not include_everyone_mentions:
        text = remove_everyone_mentions(text, message)
    text = replace_custom_emojis(text)
    text = replace_unicode_emojis(text)
    return normalize_spaces(text)


def clean_message_text(
    message,
    *,
    include_user_mentions=True,
    include_role_mentions=True,
    include_everyone_mentions=True,
):
    text = process_message_text(
        message.content or "",
        message,
        include_user_mentions=include_user_mentions,
        include_role_mentions=include_role_mentions,
        include_everyone_mentions=include_everyone_mentions,
    )
    extra = get_sticker_text(message) + get_regular_attachment_text(message)
    if extra:
        text = f"{text}. {'. '.join(extra)}" if text else ". ".join(extra)
    return normalize_spaces(text)


def get_media_caption(message):
    return process_message_text(
        remove_urls(message.content or ""),
        message,
        include_user_mentions=False,
        include_role_mentions=False,
        include_everyone_mentions=False,
    )


async def get_reply_target_name(message):
    if not message.reference:
        return None
    resolved = message.reference.resolved
    if isinstance(resolved, discord.Message):
        return get_spoken_name(resolved.author)
    return None


def format_mention_targets(user_names, role_names, mention_everyone=False):
    targets = [f"a {name}" for name in user_names]
    targets.extend(f"al rol {name}" for name in role_names)
    if mention_everyone:
        targets.append("a todos")
    return format_name_list(targets)


def format_mentioned_targets(names):
    return format_name_list([f"a {name}" for name in names])


def build_mention_phrase(author_name, user_names, role_names, mention_everyone=False):
    targets = format_mention_targets(user_names, role_names, mention_everyone)
    count = len(user_names) + len(role_names) + int(mention_everyone)
    if not count:
        return ""
    return f"{author_name} {'mencionó' if count == 1 else 'etiquetó'} {targets}"


def build_image_phrase(author_name, image_count, mentioned_names, mentioned_roles=None, mention_everyone=False):
    mentioned_roles = mentioned_roles or []
    phrase = build_mention_phrase(author_name, mentioned_names, mentioned_roles, mention_everyone)
    image_text = "una imagen" if image_count == 1 else f"{image_count} imágenes"
    return f"{phrase} en {image_text}" if phrase else f"{author_name} envió {image_text}"


def build_video_phrase(author_name, video_count, mentioned_names, mentioned_roles=None, mention_everyone=False):
    mentioned_roles = mentioned_roles or []
    phrase = build_mention_phrase(author_name, mentioned_names, mentioned_roles, mention_everyone)
    video_text = "un video" if video_count == 1 else f"{video_count} videos"
    return f"{phrase} en {video_text}" if phrase else f"{author_name} envió {video_text}"


def count_message_links(message):
    return len(URL_PATTERN.findall(message.content or ""))


def get_media_items(message):
    items = []
    images = count_message_images(message)
    videos = count_message_videos(message)
    links = count_message_links(message)
    files = len(get_regular_attachment_text(message))
    stickers = len(get_sticker_text(message))
    if images:
        items.append("una imagen" if images == 1 else f"{images} imágenes")
    if videos:
        items.append("un video" if videos == 1 else f"{videos} videos")
    if links:
        items.append("un enlace" if links == 1 else f"{links} enlaces")
    if files:
        items.append("un archivo" if files == 1 else f"{files} archivos")
    if stickers:
        items.append("un sticker" if stickers == 1 else f"{stickers} stickers")
    return items


def build_target_clause(targets):
    return f"etiquetó {format_name_list(targets)}" if len(targets) > 1 else f"mencionó {targets[0]}"


async def build_spoken_message(message):
    """Build natural TTS text for Discord messages."""
    author_name = get_spoken_name(message.author)
    targets = get_mention_targets(message)
    caption = get_media_caption(message)
    reply_name = await get_reply_target_name(message)
    media_items = get_media_items(message)

    # Preserve previous behavior for normal text and standalone stickers/files.
    if not media_items:
        normal_text = clean_message_text(
            message,
            include_user_mentions=not bool(targets),
            include_role_mentions=not bool(targets),
            include_everyone_mentions=not bool(targets),
        )
        if targets:
            phrase = f"{author_name} {build_target_clause(targets)}"
            if reply_name:
                phrase = f"{author_name} respondió a {reply_name} y {build_target_clause(targets)}"
            return f"{phrase}: {normal_text}" if normal_text else phrase
        if not normal_text:
            return None
        if reply_name:
            return f"{author_name} responde a {reply_name}: {normal_text}"
        if should_announce_name(message.guild.id, message.author.id):
            return f"{author_name} dice: {normal_text}"
        return normal_text

    # A lone ordinary file/sticker previously went through normal text handling.
    # For all media, create one announcement so no attachment type is dropped.
    phrase = f"{author_name} envió {format_name_list(media_items)}"
    if reply_name:
        phrase = f"{author_name} respondió a {reply_name} y envió {format_name_list(media_items)}"
    if targets:
        # Preserve the established "etiquetó ... en una imagen/video" phrasing
        # for a single image/video attachment with no other media.
        if not reply_name and len(media_items) == 1 and count_message_images(message) and not count_message_videos(message) and not count_message_links(message) and not get_regular_attachment_text(message) and not get_sticker_text(message):
            phrase = f"{author_name} {build_target_clause(targets)} en {media_items[0]}"
        elif not reply_name and len(media_items) == 1 and count_message_videos(message) and not count_message_images(message) and not count_message_links(message) and not get_regular_attachment_text(message) and not get_sticker_text(message):
            phrase = f"{author_name} {build_target_clause(targets)} en {media_items[0]}"
        else:
            phrase += f" y etiquetó {format_name_list(targets)}"
    if caption:
        return f"{phrase}: {caption}" if targets else f"{phrase} y dice: {caption}"
    return phrase
