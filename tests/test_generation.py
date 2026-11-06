from copy import deepcopy

import pytest
from pydantic import ValidationError

from product_cards.generation import validate_draft
from product_cards.schemas import Draft, ProductInput, make_result


@pytest.fixture
def product():
    return ProductInput(
        name="testo 510",
        manufacturer="Testo",
        specs={"Диапазон": "0–100 гПа", "Питание": ""},
        description="Измеряет дифференциальное давление.",
    )


@pytest.fixture
def draft_data():
    sentence = "Прибор предназначен для измерения дифференциального давления. "
    return {
        "seo_title": "testo 510 — дифференциальный манометр",
        "seo_description": sentence * 15,
        "search_queries": ["testo 510", "манометр Testo", "дифференциальный манометр"],
        "commercial_block": "Для измерения дифференциального давления.",
        "evidence": [
            {
                "block": "seo_description",
                "claim": sentence.strip(),
                "source_field": "description",
                "source_quote": "Измеряет дифференциальное давление.",
            }
        ],
    }


def test_valid_draft_copies_specs(product, draft_data):
    draft = Draft.model_validate(draft_data)
    validate_draft(product, draft)
    result = make_result(product, draft)
    assert result.status == "ok"
    assert result.characteristics == {"Диапазон": "0–100 гПа", "Питание": "данных нет"}
    assert "specs.Питание" in result.missing_fields
    assert "evidence" not in result.model_dump()


@pytest.mark.parametrize(
    "field,value",
    [
        ("seo_title", "x" * 71),
        ("seo_title", "Манометр 0-"),
        ("seo_title", " "),
        ("seo_description", "x" * 799),
        ("seo_description", "x" * 1201),
        ("search_queries", ["a", "b"]),
        ("search_queries", ["a", "b", "c", "d", "e", "f"]),
        ("search_queries", ["a", "a", "b"]),
        ("search_queries", ["A", "a", "B"]),
        ("search_queries", ["a", " ", "b"]),
        ("commercial_block", " "),
    ],
)
def test_draft_constraints(draft_data, field, value):
    draft_data[field] = value
    with pytest.raises(ValidationError):
        Draft.model_validate(draft_data)


@pytest.mark.parametrize("size", [800, 1200])
def test_description_boundaries(product, draft_data, size):
    draft_data["seo_title"] = "x" * 70
    draft_data["seo_description"] = "x" * size
    draft = Draft.model_validate(draft_data)
    assert len(draft.seo_description) == size


@pytest.mark.parametrize("change", ["number", "source", "quote", "claim", "model_number"])
def test_reject_unsupported_claims(product, draft_data, change):
    data = deepcopy(draft_data)
    if change == "number":
        data["commercial_block"] = "Диапазон до 999 гПа."
    elif change == "source":
        data["evidence"][0]["source_field"] = "specs.Выдумано"
    elif change == "quote":
        data["evidence"][0]["source_quote"] = "Неверная цитата"
    elif change == "claim":
        data["evidence"][0]["claim"] = "Этого нет в ответе"
    else:
        data["commercial_block"] = "Диапазон до 510 гПа."
    with pytest.raises(ValueError):
        validate_draft(product, Draft.model_validate(data))


def test_unknown_number_attached_to_unit_is_rejected(product, draft_data):
    draft_data["commercial_block"] = "Класс защиты IP999."
    with pytest.raises(ValueError):
        validate_draft(product, Draft.model_validate(draft_data))


@pytest.mark.parametrize(
    "name,description,block",
    [
        ("510", "Измеряет дифференциальное давление.", "Диапазон до 510 гПа."),
        ("testo 510", "Измеряет дифференциальное давление.", "Для testo 5100."),
        ("testo 510", "testo 510. Измеряет дифференциальное давление.", "Диапазон до 510 гПа."),
    ],
)
def test_product_name_does_not_authorize_numbers(product, draft_data, name, description, block):
    product = product.model_copy(update={"name": name, "description": description})
    draft_data["commercial_block"] = block
    with pytest.raises(ValueError):
        validate_draft(product, Draft.model_validate(draft_data))


def test_numeric_formats_are_normalized():
    from decimal import Decimal

    from product_cards.generation import numbers

    assert numbers("±0,03 гПа; −50 °C; –20,1 °C; +100.0 °C") == {
        Decimal("0.03"),
        Decimal("-50"),
        Decimal("-20.1"),
        Decimal("100"),
    }


@pytest.mark.parametrize(
    "block", ["seo_title", "seo_description", "commercial_block", "search_queries"]
)
def test_evidence_can_reference_each_output_block(product, draft_data, block):
    value = draft_data[block]
    draft_data["evidence"][0]["block"] = block
    draft_data["evidence"][0]["claim"] = value[0] if isinstance(value, list) else value
    validate_draft(product, Draft.model_validate(draft_data))


def test_product_name_matching_ignores_case(product, draft_data):
    draft_data["seo_title"] = "Testo 510 — манометр"
    validate_draft(product, Draft.model_validate(draft_data))


def test_all_known_numbers_can_be_reused(product, draft_data):
    draft_data["commercial_block"] = "Диапазон 0–100 гПа."
    validate_draft(product, Draft.model_validate(draft_data))


def test_numeric_free_product_can_generate_numeric_free_text(product, draft_data):
    product = product.model_copy(update={"specs": {"Корпус": "ABS"}})
    validate_draft(product, Draft.model_validate(draft_data))
