import json
from pathlib import Path

import pytest

from product_cards.schemas import ProductInput


@pytest.mark.parametrize(
    "slug,expected", [("testo-510", "0 ... 100 гПа"), ("testo-105", "-50 ... +275 °C")]
)
def test_example_inputs(slug, expected):
    data = json.loads(Path(f"examples/{slug}.input.json").read_text())
    product = ProductInput.model_validate(data)
    assert product.has_facts
    assert product.specs["Диапазон измерений"] == expected
    assert product.manufacturer == "Testo"
