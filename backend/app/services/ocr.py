from __future__ import annotations

import re
from pathlib import Path

import pytesseract
from PIL import Image, ImageFilter, ImageOps
from pytesseract import Output


# ============================================================
# OCR configuration
# ============================================================

MIN_OCR_IMAGE_SIZE = 1500
MAX_OCR_IMAGE_SIZE = 4000

OCR_TIMEOUT_SECONDS = 20

# Tesseract page segmentation modes:
#
# 6  = uniform block of text
# 11 = sparse text
#
# Ingredient labels can have either dense or scattered text,
# therefore we use both and merge the results.
OCR_CONFIGS = (
    "--oem 3 --psm 6",
    "--oem 3 --psm 11",
)

# Common ingredient-list headers.
INGREDIENT_HEADER_PATTERN = re.compile(
    r"""
    \b
    (?:ingredients?|inci)
    \s*
    (?:[:=\-–—]\s*)?
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)

# Text that commonly indicates the ingredient section has ended.
SECTION_END_PATTERN = re.compile(
    r"""
    \b(
        directions?
        |instructions?
        |how\s+to\s+use
        |usage
        |warning
        |warnings
        |caution
        |storage
        |distributed\s+by
        |manufactured\s+by
        |made\s+in
        |net\s+(?:wt|weight|vol|volume)
        |best\s+before
        |expiry
        |exp
    )\b
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)

# Obvious OCR garbage.
NOISE_ONLY_PATTERN = re.compile(
    r"^[^A-Za-z]+$"
)

MULTI_SPACE_PATTERN = re.compile(
    r"\s+"
)

# Ingredient labels normally contain these characters.
ALLOWED_TOKEN_PATTERN = re.compile(
    r"[^A-Za-z0-9\s\-/().%+]"
)

# Common OCR artifacts that should not become ingredients.
OCR_NOISE_PATTERNS = (
    re.compile(r"^[xX|Il1]{2,}$"),
    re.compile(r"^[0-9]{1,4}$"),
    re.compile(r"^[^A-Za-z]*[0-9][^A-Za-z]*$"),
)


# ============================================================
# Image preprocessing
# ============================================================

def _preprocess_for_ocr(
    image_path: str | Path,
) -> Image.Image:
    """
    Prepare a product-label image for OCR.

    Processing:
        1. Validate file existence.
        2. Correct EXIF camera orientation.
        3. Convert to grayscale.
        4. Improve contrast.
        5. Sharpen text.
        6. Upscale small images.
        7. Prevent unnecessarily huge OCR images.
    """

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"OCR image not found: {image_path}"
        )

    try:
        with Image.open(image_path) as source:
            image = ImageOps.exif_transpose(source)

            # Convert to grayscale for more stable OCR.
            image = image.convert("L")

            # Improve contrast while preserving text.
            image = ImageOps.autocontrast(
                image,
                cutoff=2,
            )

            # Light sharpening improves small printed text.
            image = image.filter(
                ImageFilter.SHARPEN
            )

            # Upscale small label images.
            largest_dimension = max(image.size)

            if largest_dimension < MIN_OCR_IMAGE_SIZE:
                scale = (
                    MIN_OCR_IMAGE_SIZE
                    / float(largest_dimension)
                )

                new_size = (
                    max(1, int(image.width * scale)),
                    max(1, int(image.height * scale)),
                )

                image = image.resize(
                    new_size,
                    Image.Resampling.LANCZOS,
                )

            # Avoid unnecessarily huge OCR input.
            largest_dimension = max(image.size)

            if largest_dimension > MAX_OCR_IMAGE_SIZE:
                scale = (
                    MAX_OCR_IMAGE_SIZE
                    / float(largest_dimension)
                )

                new_size = (
                    max(1, int(image.width * scale)),
                    max(1, int(image.height * scale)),
                )

                image = image.resize(
                    new_size,
                    Image.Resampling.LANCZOS,
                )

            return image

    except FileNotFoundError:
        raise

    except Exception as exc:
        raise ValueError(
            "The supplied OCR image could not be opened or processed."
        ) from exc


def _create_ocr_variants(
    image: Image.Image,
) -> list[Image.Image]:
    """
    Create a small set of OCR-friendly image variants.

    The first variant preserves natural grayscale information.
    The second uses a mild binary threshold to help high-contrast
    printed labels.
    """

    variants = [image]

    # Otsu-style threshold approximation using PIL's histogram.
    histogram = image.histogram()

    total_pixels = sum(histogram)

    if total_pixels > 0:
        weighted_sum = sum(
            index * count
            for index, count in enumerate(histogram)
        )

        threshold = int(
            weighted_sum / total_pixels
        )

        threshold = max(
            80,
            min(210, threshold),
        )

        binary = image.point(
            lambda pixel: (
                255
                if pixel >= threshold
                else 0
            )
        )

        variants.append(binary)

    return variants


# ============================================================
# Tesseract availability
# ============================================================

def _verify_tesseract() -> None:
    """
    Verify that the Tesseract executable is available.

    pytesseract is only a Python wrapper; the actual Tesseract
    OCR engine must also be installed and available.
    """

    try:
        pytesseract.get_tesseract_version()

    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract OCR is not installed or is not available "
            "in PATH. Install Tesseract OCR and restart the backend."
        ) from exc

    except Exception as exc:
        raise RuntimeError(
            "Tesseract OCR could not be initialized."
        ) from exc


# ============================================================
# OCR text extraction
# ============================================================

def _run_single_ocr(
    image: Image.Image,
    config: str,
) -> str:
    """
    Run one Tesseract OCR pass.
    """

    try:
        text = pytesseract.image_to_string(
            image,
            lang="eng",
            config=config,
            timeout=OCR_TIMEOUT_SECONDS,
        )

        return text.strip()

    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract OCR is not installed or is not available in PATH."
        ) from exc

    except RuntimeError as exc:
        # pytesseract raises RuntimeError for timeout.
        message = str(exc).lower()

        if "timeout" in message:
            raise RuntimeError(
                "OCR processing took too long. "
                "Please upload a clearer or smaller image."
            ) from exc

        raise RuntimeError(
            "Tesseract OCR failed while reading the image."
        ) from exc


def extract_text(
    image_path: str | Path,
) -> str:
    """
    Run Tesseract OCR on a product-label image.

    Multiple preprocessing variants and page segmentation
    configurations are used to improve robustness.

    Returns:
        Cleaned raw OCR text.

    Raises:
        FileNotFoundError:
            Image does not exist.

        ValueError:
            Image cannot be processed.

        RuntimeError:
            Tesseract is unavailable or OCR fails.
    """

    _verify_tesseract()

    processed = _preprocess_for_ocr(
        image_path
    )

    variants = _create_ocr_variants(
        processed
    )

    collected_text: list[str] = []

    for variant in variants:
        for config in OCR_CONFIGS:
            text = _run_single_ocr(
                variant,
                config,
            )

            if text:
                collected_text.append(text)

    if not collected_text:
        return ""

    # Merge OCR passes while preserving useful lines.
    merged_lines: list[str] = []
    seen_lines: set[str] = set()

    for text in collected_text:
        for line in text.splitlines():
            cleaned_line = _normalize_ocr_line(
                line
            )

            if not cleaned_line:
                continue

            key = cleaned_line.casefold()

            if key in seen_lines:
                continue

            seen_lines.add(key)
            merged_lines.append(
                cleaned_line
            )

    return "\n".join(
        merged_lines
    ).strip()


# ============================================================
# OCR normalization
# ============================================================

def _normalize_ocr_line(
    line: str,
) -> str:
    """
    Normalize one OCR line without attempting to identify
    ingredients yet.
    """

    if not line:
        return ""

    value = str(line)

    value = value.replace(
        "\u00a0",
        " ",
    )

    value = value.replace(
        "\t",
        " ",
    )

    value = value.replace(
        "\r",
        " ",
    )

    value = MULTI_SPACE_PATTERN.sub(
        " ",
        value,
    )

    return value.strip()


def _clean_ocr_token(
    token: str,
) -> str:
    """
    Normalize one OCR ingredient candidate.

    Keeps useful cosmetic ingredient characters:
        letters
        numbers
        spaces
        hyphens
        slashes
        parentheses
        periods
        percentages
        plus signs
    """

    if not token:
        return ""

    value = str(token)

    # Normalize Unicode compatibility characters.
    value = value.replace(
        "\u00a0",
        " ",
    )

    value = value.replace(
        "–",
        "-",
    )

    value = value.replace(
        "—",
        "-",
    )

    value = value.replace(
        "−",
        "-",
    )

    value = value.replace(
        "·",
        " ",
    )

    value = ALLOWED_TOKEN_PATTERN.sub(
        "",
        value,
    )

    value = MULTI_SPACE_PATTERN.sub(
        " ",
        value,
    )

    value = value.strip(
        " \t\r\n,;:|•·"
    )

    return value.strip()


def _looks_like_ocr_noise(
    token: str,
) -> bool:
    """
    Reject obvious OCR garbage.
    """

    if not token:
        return True

    if len(token) < 2:
        return True

    if NOISE_ONLY_PATTERN.fullmatch(token):
        return True

    for pattern in OCR_NOISE_PATTERNS:
        if pattern.fullmatch(token):
            return True

    # A valid ingredient candidate should contain letters.
    if not re.search(
        r"[A-Za-z]",
        token,
    ):
        return True

    return False


# ============================================================
# Ingredient section extraction
# ============================================================

def _extract_ingredient_section(
    raw_text: str,
) -> str:
    """
    Extract the most likely ingredient-list portion.

    If an Ingredients/INCI header exists, text before that header
    is ignored.

    If a known following section begins, extraction stops there.

    If no ingredient header exists, the full OCR text is returned
    because some product labels omit the explicit header.
    """

    if not raw_text:
        return ""

    text = raw_text.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    header_match = INGREDIENT_HEADER_PATTERN.search(
        text
    )

    if header_match:
        section = text[
            header_match.end():
        ]
    else:
        section = text

    # Stop at an obvious subsequent label section.
    end_match = SECTION_END_PATTERN.search(
        section
    )

    if end_match:
        section = section[
            :end_match.start()
        ]

    return section.strip()


# ============================================================
# Ingredient token extraction
# ============================================================

def extract_ingredient_tokens(
    raw_text: str,
) -> list[str]:
    """
    Extract ingredient candidates from OCR text.

    Supported ingredient headers:
        Ingredients:
        Ingredient:
        INCI:
        Ingredients -
        INCI -

    Common separators:
        commas
        semicolons
        bullets
        line breaks

    Returns:
        Normalized, deduplicated ingredient candidates.
    """

    if not raw_text:
        return []

    text = _extract_ingredient_section(
        raw_text
    )

    if not text:
        return []

    # Normalize line endings.
    text = text.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    # Convert bullets and common separators into commas.
    text = text.replace(
        "•",
        ",",
    )

    text = text.replace(
        "·",
        ",",
    )

    # Ingredient labels sometimes use dots between ingredients.
    # Do not globally replace periods because decimal percentages
    # and ingredient names can contain them.
    text = re.sub(
        r"\s*;\s*",
        ",",
        text,
    )

    # Split ingredient candidates.
    raw_tokens = re.split(
        r"[,;\n]+",
        text,
    )

    tokens: list[str] = []
    seen: set[str] = set()

    for raw_token in raw_tokens:
        cleaned = _clean_ocr_token(
            raw_token
        )

        if _looks_like_ocr_noise(
            cleaned
        ):
            continue

        # Avoid extremely long chunks caused by OCR failure.
        if len(cleaned) > 180:
            continue

        normalized_key = (
            cleaned
            .casefold()
            .strip()
        )

        if normalized_key in seen:
            continue

        seen.add(
            normalized_key
        )

        tokens.append(
            cleaned
        )

    return tokens


# ============================================================
# OCR confidence helper
# ============================================================

def get_ocr_confidence(
    image_path: str | Path,
) -> float:
    """
    Estimate OCR confidence using Tesseract's word-level data.

    Returns:
        Average confidence from recognized words, scaled 0-100.

    This is an OCR quality indicator only. It is NOT ingredient
    safety confidence.
    """

    _verify_tesseract()

    processed = _preprocess_for_ocr(
        image_path
    )

    try:
        data = pytesseract.image_to_data(
            processed,
            lang="eng",
            config="--oem 3 --psm 6",
            output_type=Output.DICT,
            timeout=OCR_TIMEOUT_SECONDS,
        )

    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract OCR is not installed or is not available in PATH."
        ) from exc

    except RuntimeError as exc:
        raise RuntimeError(
            "OCR confidence analysis timed out."
        ) from exc

    confidences: list[float] = []

    for raw_confidence, text in zip(
        data.get("conf", []),
        data.get("text", []),
    ):
        if not str(text).strip():
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

        if confidence >= 0:
            confidences.append(
                confidence
            )

    if not confidences:
        return 0.0

    return round(
        max(
            0.0,
            min(
                100.0,
                sum(confidences)
                / len(confidences),
            ),
        ),
        2,
    )


# ============================================================
# Combined OCR helper
# ============================================================

def extract_ingredients_from_image(
    image_path: str | Path,
) -> dict:
    """
    Convenience helper for the Ingredient Scanner.

    Returns:

        {
            "text": "...",
            "ingredients": [...],
            "ocr_confidence": 0.0
        }

    This function does not perform ingredient database matching.
    Database matching remains the responsibility of
    ingredient_matching.py.
    """

    raw_text = extract_text(
        image_path
    )

    ingredients = extract_ingredient_tokens(
        raw_text
    )

    try:
        confidence = get_ocr_confidence(
            image_path
        )
    except RuntimeError:
        # OCR text itself is already available. Do not make the
        # optional confidence calculation break the complete scan.
        confidence = 0.0

    return {
        "text": raw_text,
        "ingredients": ingredients,
        "ocr_confidence": confidence,
    }