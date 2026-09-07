import asyncio
import io
import re

from PIL import (
    Image,
    ImageEnhance,
    ImageOps,
)

import pytesseract
from pytesseract import Output


# ============================================================
# CONFIGURACIÓN
# ============================================================

OCR_LANGUAGE = "spa"
MAX_OCR_CHARACTERS = 1200

# Escala aplicada antes de pasar la imagen a Tesseract.
OCR_SCALE = 2


# ------------------------------------------------------------
# SALIDA TEMPRANA
#
# Si encontramos un resultado suficientemente bueno,
# detenemos el OCR inmediatamente.
# ------------------------------------------------------------

FAST_ACCEPT_CONFIDENCE = 82.0
FAST_ACCEPT_MIN_CHARS = 8
FAST_ACCEPT_MIN_WORDS = 2


# ------------------------------------------------------------
# FALLBACKS
# ------------------------------------------------------------

THRESHOLD_FALLBACK_CONFIDENCE = 72.0
COLOR_FALLBACK_CONFIDENCE = 60.0


THRESHOLDS = (
    110,
    150,
    190,
)


# ============================================================
# VALIDAR IMAGEN
# ============================================================

def is_supported_image(
    attachment,
):
    """
    Indica si un attachment de Discord es una imagen
    compatible con OCR.

    Los GIF se excluyen.
    """

    content_type = (
        attachment.content_type
        or ""
    ).lower()

    filename = (
        attachment.filename
        or ""
    ).lower()

    if (
        content_type == "image/gif"
        or filename.endswith(".gif")
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
# UTILIDADES DE TEXTO
# ============================================================

def normalize_ocr_text(
    text,
):
    if not text:
        return ""

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    if (
        len(text)
        > MAX_OCR_CHARACTERS
    ):
        text = (
            text[
                :MAX_OCR_CHARACTERS
            ].rstrip()
            + "..."
        )

    return text


def count_useful_chars(
    text,
):
    return sum(
        character.isalnum()
        for character in text
    )


def count_words(
    text,
):
    return sum(
        1
        for word in text.split()
        if any(
            character.isalnum()
            for character in word
        )
    )


def is_good_result(
    text,
    confidence,
):
    if not text:
        return False

    if (
        confidence
        < FAST_ACCEPT_CONFIDENCE
    ):
        return False

    if (
        count_useful_chars(
            text
        )
        < FAST_ACCEPT_MIN_CHARS
    ):
        return False

    if (
        count_words(
            text
        )
        < FAST_ACCEPT_MIN_WORDS
    ):
        return False

    return True


# ============================================================
# PREPROCESADO
# ============================================================

def resize_for_ocr(
    image,
):
    if OCR_SCALE <= 1:
        return image

    width, height = (
        image.size
    )

    return image.resize(
        (
            width * OCR_SCALE,
            height * OCR_SCALE,
        ),
        Image.Resampling.LANCZOS,
    )


def prepare_grayscale(
    image,
):
    image = ImageOps.grayscale(
        image
    )

    image = ImageOps.autocontrast(
        image
    )

    return resize_for_ocr(
        image
    )


def prepare_high_contrast(
    image,
):
    image = prepare_grayscale(
        image
    )

    return (
        ImageEnhance.Contrast(
            image
        ).enhance(
            2.2
        )
    )


def prepare_inverted(
    image,
):
    return ImageOps.invert(
        prepare_grayscale(
            image
        )
    )


def prepare_threshold(
    grayscale_image,
    threshold,
    *,
    invert=False,
):
    image = ImageOps.autocontrast(
        grayscale_image
    )

    image = resize_for_ocr(
        image
    )

    image = image.point(
        lambda pixel: (
            255
            if pixel > threshold
            else 0
        )
    )

    if invert:
        image = ImageOps.invert(
            image
        )

    return image


# ============================================================
# FALLBACK DE COLOR
# ============================================================

def make_color_candidates(
    image,
):
    """
    Crea pocas variantes de color.

    Antes probábamos demasiados canales y thresholds.
    Ahora solo usamos los candidatos que más suelen ayudar.
    """

    candidates = []

    # --------------------------------------------------------
    # RGB
    # --------------------------------------------------------

    rgb = image.convert(
        "RGB"
    )

    _red, green, blue = (
        rgb.split()
    )

    for channel in (
        green,
        blue,
    ):
        channel = ImageOps.autocontrast(
            channel
        )

        channel = resize_for_ocr(
            channel
        )

        candidates.append(
            channel
        )

        candidates.append(
            ImageOps.invert(
                channel
            )
        )

    # --------------------------------------------------------
    # HSV VALUE
    #
    # El canal de luminosidad suele ser bastante útil
    # para texto sobre fondos de colores.
    # --------------------------------------------------------

    hsv = image.convert(
        "HSV"
    )

    _hue, _saturation, value = (
        hsv.split()
    )

    value = ImageOps.autocontrast(
        value
    )

    value = resize_for_ocr(
        value
    )

    candidates.append(
        value
    )

    candidates.append(
        ImageOps.invert(
            value
        )
    )

    return candidates


# ============================================================
# TESSERACT
# ============================================================

def run_tesseract(
    image,
    *,
    psm,
):
    data = pytesseract.image_to_data(
        image,
        lang=OCR_LANGUAGE,
        output_type=Output.DICT,
        config=f"--psm {psm}",
    )

    words = []
    confidences = []

    for (
        raw_text,
        raw_confidence,
    ) in zip(
        data["text"],
        data["conf"],
    ):
        word = raw_text.strip()

        if not word:
            continue

        try:
            confidence = float(
                raw_confidence
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        if confidence < 0:
            continue

        words.append(
            word
        )

        confidences.append(
            confidence
        )

    if not words:
        return (
            "",
            0.0,
            0.0,
        )

    text = " ".join(
        words
    )

    confidence = (
        sum(confidences)
        / len(confidences)
    )

    useful_chars = (
        count_useful_chars(
            text
        )
    )

    # --------------------------------------------------------
    # SCORE
    #
    # La confianza es lo principal.
    # Los bonuses favorecen resultados con algo de contenido
    # real en vez de una palabra aislada.
    # --------------------------------------------------------

    score = (
        confidence
        + min(
            len(words),
            20,
        )
        * 0.6
        + min(
            useful_chars,
            100,
        )
        * 0.08
    )

    return (
        text,
        confidence,
        score,
    )


# ============================================================
# PROBAR CANDIDATOS
# ============================================================

def evaluate_candidates(
    candidates,
    *,
    psm_modes,
    fast_exit=False,
):
    best_text = ""
    best_confidence = 0.0
    best_score = 0.0

    for image in candidates:
        for psm in psm_modes:
            try:
                (
                    text,
                    confidence,
                    score,
                ) = run_tesseract(
                    image,
                    psm=psm,
                )

            except Exception as exc:
                print(
                    "[OCR] Error en variante: "
                    f"{exc}"
                )

                continue

            if score > best_score:
                best_text = text
                best_confidence = (
                    confidence
                )
                best_score = score

            if (
                fast_exit
                and is_good_result(
                    text,
                    confidence,
                )
            ):
                return (
                    text,
                    confidence,
                    score,
                    True,
                )

    return (
        best_text,
        best_confidence,
        best_score,
        False,
    )


# ============================================================
# ACTUALIZAR MEJOR RESULTADO
# ============================================================

def choose_better_result(
    current,
    candidate,
):
    current_text, current_confidence, current_score = (
        current
    )

    candidate_text, candidate_confidence, candidate_score = (
        candidate
    )

    if (
        candidate_score
        > current_score
    ):
        return (
            candidate_text,
            candidate_confidence,
            candidate_score,
        )

    return (
        current_text,
        current_confidence,
        current_score,
    )


# ============================================================
# OCR PRINCIPAL
# ============================================================

def run_ocr(
    image_bytes,
):
    # --------------------------------------------------------
    # ABRIR IMAGEN
    # --------------------------------------------------------

    try:
        image = Image.open(
            io.BytesIO(
                image_bytes
            )
        )

        image = ImageOps.exif_transpose(
            image
        )

        image = image.convert(
            "RGB"
        )

    except Exception as exc:
        print(
            "[OCR] No pude abrir imagen: "
            f"{exc}"
        )

        return ""

    best = (
        "",
        0.0,
        0.0,
    )

    # ========================================================
    # FASE 1 — RÁPIDA
    #
    # Capturas normales deberían terminar aquí.
    # ========================================================

    grayscale = prepare_grayscale(
        image
    )

    high_contrast = (
        prepare_high_contrast(
            image
        )
    )

    (
        text,
        confidence,
        score,
        accepted,
    ) = evaluate_candidates(
        (
            grayscale,
            high_contrast,
        ),
        psm_modes=(
            6,
        ),
        fast_exit=True,
    )

    best = choose_better_result(
        best,
        (
            text,
            confidence,
            score,
        ),
    )

    if accepted:
        result = normalize_ocr_text(
            text
        )

        print(
            "[OCR] Aceptado rápido "
            f"({confidence:.1f}%): "
            f"{result[:150]}"
        )

        return result

    # ========================================================
    # FASE 2 — TEXTO DISPERSO
    #
    # PSM 11 funciona mejor cuando el texto no forma
    # un bloque uniforme.
    # ========================================================

    inverted = prepare_inverted(
        image
    )

    (
        text,
        confidence,
        score,
        accepted,
    ) = evaluate_candidates(
        (
            grayscale,
            high_contrast,
            inverted,
        ),
        psm_modes=(
            11,
        ),
        fast_exit=True,
    )

    best = choose_better_result(
        best,
        (
            text,
            confidence,
            score,
        ),
    )

    if accepted:
        result = normalize_ocr_text(
            text
        )

        print(
            "[OCR] Aceptado PSM 11 "
            f"({confidence:.1f}%): "
            f"{result[:150]}"
        )

        return result

    # ========================================================
    # FASE 3 — THRESHOLDS
    # ========================================================

    (
        best_text,
        best_confidence,
        best_score,
    ) = best

    if (
        best_confidence
        < THRESHOLD_FALLBACK_CONFIDENCE
    ):
        raw_grayscale = (
            ImageOps.grayscale(
                image
            )
        )

        threshold_candidates = []

        for threshold in (
            THRESHOLDS
        ):
            threshold_candidates.append(
                prepare_threshold(
                    raw_grayscale,
                    threshold,
                )
            )

            threshold_candidates.append(
                prepare_threshold(
                    raw_grayscale,
                    threshold,
                    invert=True,
                )
            )

        (
            text,
            confidence,
            score,
            accepted,
        ) = evaluate_candidates(
            threshold_candidates,
            psm_modes=(
                6,
            ),
            fast_exit=True,
        )

        best = choose_better_result(
            best,
            (
                text,
                confidence,
                score,
            ),
        )

        if accepted:
            result = (
                normalize_ocr_text(
                    text
                )
            )

            print(
                "[OCR] Aceptado por threshold "
                f"({confidence:.1f}%): "
                f"{result[:150]}"
            )

            return result

    # ========================================================
    # FASE 4 — COLOR
    #
    # Último recurso.
    # ========================================================

    (
        best_text,
        best_confidence,
        best_score,
    ) = best

    if (
        best_confidence
        < COLOR_FALLBACK_CONFIDENCE
    ):
        (
            text,
            confidence,
            score,
            accepted,
        ) = evaluate_candidates(
            make_color_candidates(
                image
            ),
            psm_modes=(
                6,
                11,
            ),
            fast_exit=True,
        )

        best = choose_better_result(
            best,
            (
                text,
                confidence,
                score,
            ),
        )

        if accepted:
            result = normalize_ocr_text(
                text
            )

            print(
                "[OCR] Aceptado por color "
                f"({confidence:.1f}%): "
                f"{result[:150]}"
            )

            return result

    # ========================================================
    # RESULTADO FINAL
    # ========================================================

    (
        best_text,
        best_confidence,
        _best_score,
    ) = best

    result = normalize_ocr_text(
        best_text
    )

    if not result:
        print(
            "[OCR] No se detectó texto."
        )

        return ""

    print(
        "[OCR] Texto detectado "
        f"({best_confidence:.1f}%): "
        f"{result[:150]}"
    )

    return result


# ============================================================
# API PÚBLICA PARA DISCORD
# ============================================================

async def get_attachment_ocr_text(
    attachment,
):
    """
    Ejecuta OCR sobre una imagen adjunta de Discord.

    Esta es la única función de OCR que necesita bot.py.
    """

    if not is_supported_image(
        attachment
    ):
        return ""

    try:
        image_bytes = (
            await attachment.read()
        )

    except Exception as exc:
        print(
            "[OCR] Error descargando imagen: "
            f"{exc}"
        )

        return ""

    try:
        return await asyncio.to_thread(
            run_ocr,
            image_bytes,
        )

    except Exception as exc:
        print(
            "[OCR] Error ejecutando OCR: "
            f"{exc}"
        )

        return ""
