import numpy as np
from PIL import Image

from app.services.skin_analysis import preprocess_image


def test_image_preprocessing():
    # Create a temporary RGB image with a non-square size
    image = Image.new("RGB", (500, 300), color=(120, 180, 200))

    image_path = "tests/test_input_image.jpg"
    image.save(image_path)

    # Run the actual project preprocessing function
    result = preprocess_image(image_path)

    # Check the output type
    assert isinstance(result, np.ndarray)

    # Check batch + image dimensions
    assert result.shape == (1, 224, 224, 3)

    # Check data type
    assert result.dtype == np.float32

    # Check that RGB channels are present
    assert result.shape[-1] == 3


def test_invalid_image_path():
    try:
        preprocess_image("tests/nonexistent_image.jpg")
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        assert True


def test_invalid_image_file():
    invalid_file = "tests/invalid_image.txt"

    with open(invalid_file, "w", encoding="utf-8") as file:
        file.write("This is not an image.")

    try:
        preprocess_image(invalid_file)
        assert False, "Expected ValueError"
    except ValueError:
        assert True