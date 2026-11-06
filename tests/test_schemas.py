import pytest
from pydantic import ValidationError

from product_cards.schemas import ProductInput, make_result


def test_name_only_needs_clarification():
    result = make_result(ProductInput(name="Манометр"))
    assert result.status == "needs_clarification"
    assert result.seo_title is None
    assert result.search_queries == []
    assert "description" in result.missing_fields
    assert "specs" in result.missing_fields


def test_whitespace_input():
    with pytest.raises(ValidationError):
        ProductInput(name="  ")
    result = make_result(ProductInput(name=" Прибор ", description="  ", specs={"Питание": " "}))
    assert result.status == "needs_clarification"
    assert result.characteristics == {"Питание": "данных нет"}
    assert "specs.Питание" in result.missing_fields


@pytest.mark.parametrize(
    "data",
    [
        {"name": 42},
        {"name": "A", "specs": {"a": 12}},
        {"name": "A", "unexpected": "x"},
        {"name": "A", "specs": {" ": "x"}},
        {"name": "A", "description": "x" * 20001},
    ],
)
def test_invalid_input(data):
    with pytest.raises(ValidationError):
        ProductInput.model_validate(data)


@pytest.mark.parametrize(
    "field,limit", [("name", 200), ("manufacturer", 200), ("description", 20000)]
)
def test_string_field_limits(field, limit):
    assert (
        getattr(ProductInput.model_validate({"name": "A", field: "x" * limit}), field)
        == "x" * limit
    )
    with pytest.raises(ValidationError):
        ProductInput.model_validate({"name": "A", field: "x" * (limit + 1)})


def test_specification_limits():
    assert ProductInput(name="A", specs={"k" * 200: "v" * 1000}).has_facts
    assert len(ProductInput(name="A", specs={str(i): "x" for i in range(100)}).specs) == 100
    for specs in [{"k" * 201: "v"}, {"k": "v" * 1001}, {str(i): "v" for i in range(101)}]:
        with pytest.raises(ValidationError):
            ProductInput(name="A", specs=specs)


@pytest.mark.parametrize(
    "fields,expected",
    [
        ({"description": "Описание"}, True),
        ({"specs": {"Корпус": "ABS"}}, True),
        ({"description": " ", "specs": {"Корпус": " "}}, False),
    ],
)
def test_facts_can_come_from_either_source(fields, expected):
    assert ProductInput(name="A", **fields).has_facts is expected


def test_whitespace_is_trimmed_in_all_inputs():
    product = ProductInput(
        name=" A ", manufacturer=" Testo ", description=" Текст ", specs={" Корпус ": " ABS "}
    )
    assert product.name == "A"
    assert product.manufacturer == "Testo"
    assert product.description == "Текст"
    assert product.specs == {"Корпус": "ABS"}


def test_python_bytes_are_not_silently_coerced_to_text():
    with pytest.raises(ValidationError):
        ProductInput(name=b"A")
