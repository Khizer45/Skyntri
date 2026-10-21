from types import SimpleNamespace

from app.services.ingredient_matching import (
    match_ingredients,
    normalize_ingredient_name,
)


class FakeQuery:
    def __init__(self, ingredients):
        self.ingredients = ingredients

    def all(self):
        return self.ingredients


class FakeDB:
    def __init__(self, ingredients):
        self.ingredients = ingredients

    def query(self, model):
        return FakeQuery(self.ingredients)


def create_ingredient(
    ingredient_id,
    name,
    inci_name=None,
    aliases_json="[]",
    precautions=None,
    avoid_skin_types_json="[]",
):
    return SimpleNamespace(
        id=ingredient_id,
        name=name,
        inci_name=inci_name,
        aliases_json=aliases_json,
        precautions=precautions,
        avoid_skin_types_json=avoid_skin_types_json,
    )


def test_normalize_ingredient_name():
    assert normalize_ingredient_name(
        "  Sodium   Hyaluronate  "
    ) == "sodium hyaluronate"

    assert normalize_ingredient_name(
        "NIACINAMIDE"
    ) == "niacinamide"


def test_exact_ingredient_match():
    ingredient = create_ingredient(
        1,
        "Niacinamide",
    )

    db = FakeDB([ingredient])

    result = match_ingredients(
        ["Niacinamide"],
        db,
    )

    assert len(result["matched"]) == 1
    assert result["matched"][0]["ingredient"].name == "Niacinamide"
    assert result["matched"][0]["score"] == 100.0
    assert result["unmatched"] == []


def test_fuzzy_ingredient_match():
    ingredient = create_ingredient(
        2,
        "Hyaluronic Acid",
    )

    db = FakeDB([ingredient])

    result = match_ingredients(
        ["Hyaluronic Acd"],
        db,
    )

    assert len(result["matched"]) == 1
    assert result["matched"][0]["ingredient"].name == "Hyaluronic Acid"
    assert result["matched"][0]["score"] >= 82.0


def test_unmatched_ingredient():
    ingredient = create_ingredient(
        3,
        "Salicylic Acid",
    )

    db = FakeDB([ingredient])

    result = match_ingredients(
        ["CompletelyUnknownIngredient"],
        db,
    )

    assert result["matched"] == []
    assert result["unmatched"] == [
        "CompletelyUnknownIngredient"
    ]


def test_duplicate_ingredient_is_not_returned_twice():
    ingredient = create_ingredient(
        4,
        "Vitamin C",
    )

    db = FakeDB([ingredient])

    result = match_ingredients(
        ["Vitamin C", "vitamin c"],
        db,
    )

    assert len(result["matched"]) == 1
    assert result["matched"][0]["ingredient"].name == "Vitamin C"