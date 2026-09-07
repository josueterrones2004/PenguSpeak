import asyncio
import os
import uuid

import discord
import edge_tts

from penguspeak.state import guild_audio_locks
from penguspeak.voices import VOICES


TEMP_DIR = "temp"

os.makedirs(
    TEMP_DIR,
    exist_ok=True,
)


async def generate_edge_file(
    text,
    voice_id,
):
    data = VOICES.get(
        voice_id
    )

    if not data:
        return None

    filepath = os.path.join(
        TEMP_DIR,
        f"{uuid.uuid4()}.mp3",
    )

    communicate = edge_tts.Communicate(
        text,
        data["voice"],
    )

    await communicate.save(
        filepath
    )

    return filepath


async def create_audio_file(
    text,
    voice_id,
):
    data = VOICES.get(
        voice_id
    )

    if not data:
        return None

    if data["engine"] != "edge":
        return None

    return await generate_edge_file(
        text,
        voice_id,
    )


async def play_audio(
    bot,
    guild_id,
    voice_client,
    filepath,
):
    lock = guild_audio_locks.setdefault(
        guild_id,
        asyncio.Lock(),
    )

    async with lock:
        finished = asyncio.Event()

        source = discord.FFmpegPCMAudio(
            filepath
        )

        def after_playing(
            error,
        ):
            if error:
                print(
                    "Error reproduciendo audio: "
                    f"{error}"
                )

            bot.loop.call_soon_threadsafe(
                finished.set
            )

        voice_client.play(
            source,
            after=after_playing,
        )

        await finished.wait()

    try:
        os.remove(
            filepath
        )

    except FileNotFoundError:
        pass
