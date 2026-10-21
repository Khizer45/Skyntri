from unittest.mock import patch

import numpy as np

from app.services.skin_analysis import predict_dataset3


def test_multi_label_threshold_logic():
    # Sample probabilities for the 10 classes.
    # Values are intentionally chosen around the actual thresholds.
    sample_prediction = np.array([
        [0.50,  # Acne      -> 0.50 >= 0.46 -> detected
         0.20,  # Blackheads-> 0.20 < 0.34 -> not detected
         0.40,  # Dark Spots-> 0.40 >= 0.36 -> detected
         0.36,  # Dry Skin  -> 0.36 >= 0.36 -> detected
         0.10,  # Eye bags  -> 0.10 < 0.27 -> not detected
         0.30,  # Normal    -> 0.30 >= 0.29 -> detected
         0.35,  # Oily Skin -> 0.35 < 0.36 -> not detected
         0.40,  # Pores     -> 0.40 >= 0.38 -> detected
         0.26,  # Redness   -> 0.26 < 0.27 -> not detected
         0.25,  # Wrinkles  -> 0.25 >= 0.20 -> detected
        ]
    ])

    class FakeModel:
        def predict(self, image_array, verbose=0):
            return sample_prediction

    with patch(
        "app.services.skin_analysis.load_dataset3_model",
        return_value=FakeModel(),
    ):
        result = predict_dataset3(
            np.zeros((1, 224, 224, 3), dtype=np.float32)
        )

    expected_conditions = [
        "Acne",
        "Dark Spots",
        "Dry Skin",
        "Normal Skin",
        "Pores",
        "Wrinkles",
    ]

    assert result["conditions"] == expected_conditions

    # Verify a detected class
    assert result["probabilities"]["Acne"]["detected"] is True

    # Verify a non-detected class
    assert result["probabilities"]["Blackheads"]["detected"] is False


def test_threshold_boundary():
    sample_prediction = np.array([
        [0.46, 0.34, 0.36, 0.36, 0.27,
         0.29, 0.36, 0.38, 0.27, 0.20]
    ])

    class FakeModel:
        def predict(self, image_array, verbose=0):
            return sample_prediction

    with patch(
        "app.services.skin_analysis.load_dataset3_model",
        return_value=FakeModel(),
    ):
        result = predict_dataset3(
            np.zeros((1, 224, 224, 3), dtype=np.float32)
        )

    # Since the implementation uses >=,
    # values exactly equal to the threshold must be detected.
    assert len(result["conditions"]) == 10