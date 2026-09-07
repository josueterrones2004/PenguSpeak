import asyncio
import io
import re

import pytesseract

from PIL import Image, ImageOps


# ============================================================
# CONFIGURACIÓN
# ============================================================

OCR_LANGUAGE = "spa"

# Evita que una captura enorme meta varios minutos
# de texto al canal de voz.
MAX_OCR_CHARACTERS = 1200


# ============================================================
# UTILIDADES
# ============================================================

def normalize_ocr_text(text):
    text = text.replace(
        "\r",
        "\n",
    )

    # Unimos líneas consecutivas.
    text = re.sub(
        r"\n+",
        ". ",
        text,
    )

    # Quitamos espacios duplicados.
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def is_supported_image(
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

    # GIF ignorado.
    if (
        filename.endswith(".gif")
        or content_type == "image/gif"
    ):
        return False

    if content_type.startswith(
        "image/"
    ):
        return True

    return filename.endswith(
        (
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".bmp",
        )
    )


# ============================================================
# OCR
# ============================================================

def run_ocr(
    image_bytes,
):
    """
    Procesa una imagen en un hilo separado para no
    bloquear el event loop de Discord.
    """

    with Image.open(
        io.BytesIO(
            image_bytes
        )
    ) as image:

        # Corregir orientación de fotos.
        image = ImageOps.exif_transpose(
            image
        )

        # RGB evita problemas con algunos formatos.
        image = image.convert(
            "RGB"
        )

        text = pytesseract.image_to_string(
            image,
            lang=OCR_LANGUAGE,
        )

    text = normalize_ocr_text(
        text
    )

    if not text:
        return None

    if len(text) > MAX_OCR_CHARACTERS:
        text = (
            text[
                :MAX_OCR_CHARACTERS
            ].rstrip()
            + "..."
        )

    return text


async def read_attachment_text(
    attachment,
):
    if not is_supported_image(
        attachment
    ):
        return None

    try:
        image_bytes = await attachment.read()

    except Exception as exc:
        print(
            "[OCR] No se pudo descargar "
            f"{attachment.filename}: {exc}"
        )

        return None

    try:
        text = await asyncio.to_thread(
            run_ocr,
            image_bytes,
        )

    except Exception as exc:
        print(
            "[OCR] Error procesando "
            f"{attachment.filename}: {exc}"
        )

        return None

    if text:
        print(
            "[OCR] Texto detectado en "
            f"{attachment.filename}: "
            f"{text[:150]}"
        )

    return text


async def get_message_ocr_text(
    message,
):
    """
    Lee todas las imágenes de un mensaje.

    Si hay varias imágenes con texto:
        Texto de la imagen: ...
        Texto de otra imagen: ...
    """

    results = []

    for attachment in message.attachments:
        if not is_supported_image(
            attachment
        ):
            continue

        text = await read_attachment_text(
            attachment
        )

        if text:
            results.append(
                text
            )

    return results
