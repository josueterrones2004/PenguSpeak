
import asyncio
import os
import time
from xml.sax.saxutils import escape

import aiohttp
from dotenv import load_dotenv

load_dotenv()

VOICE = "es-MX-JorgeNeural"
TEXT = "Hola, esta es una prueba de velocidad de PenguSpeak con Azure."


async def main():
    key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION")

    if not key or not region:
        raise RuntimeError(
            "Configura AZURE_SPEECH_KEY y "
            "AZURE_SPEECH_REGION en .env"
        )

    url = (
        f"https://{region}.tts.speech.microsoft.com"
        "/cognitiveservices/v1"
    )

    ssml = (
        '<speak version="1.0" '
        'xmlns="http://www.w3.org/2001/10/synthesis" '
        'xml:lang="es-MX">'
        f'<voice name="{VOICE}">'
        f'<prosody rate="+30%">{escape(TEXT)}</prosody>'
        '</voice></speak>'
    )

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat":
            "audio-24khz-48kbitrate-mono-mp3",
        "User-Agent": "PenguSpeak/2.0-dev",
    }

    timeout = aiohttp.ClientTimeout(total=30)

    start = time.perf_counter()
    first_byte = None
    total_bytes = 0

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:
        async with session.post(
            url,
            data=ssml.encode("utf-8"),
            headers=headers,
        ) as response:
            print(f"HTTP: {response.status}")

            if response.status != 200:
                print((await response.text())[:500])
                return

            with open("azure-test.mp3", "wb") as file:
                async for chunk in (
                    response.content.iter_chunked(4096)
                ):
                    if not chunk:
                        continue

                    if first_byte is None:
                        first_byte = time.perf_counter()
                        print(
                            "Primer audio: "
                            f"{(first_byte - start) * 1000:.0f} ms"
                        )

                    file.write(chunk)
                    total_bytes += len(chunk)

    print(
        "Tiempo total: "
        f"{(time.perf_counter() - start) * 1000:.0f} ms"
    )
    print(f"Audio recibido: {total_bytes} bytes")


if __name__ == "__main__":
    asyncio.run(main())
