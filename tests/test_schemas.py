import pytest
from pydantic import ValidationError

from product_cards.schemas import ProductInput, make_result


def test_name_only_needs_clarification():
    result = make_result(ProductInput(name='Манометр'))
    assert result.status == 'needs_clarification'
    assert result.seo_title is None
    assert result.search_queries == []
    assert 'description' in result.missing_fields
    assert 'specs' in result.missing_fields


def test_whitespace_input():
    with pytest.raises(ValidationError):
        ProductInput(name='  ')
    result = make_result(ProductInput(name=' Прибор ', description='  ', specs={'Питание': ' '}))
    assert result.status == 'needs_clarification'
    assert result.characteristics == {'Питание': 'данных нет'}
    assert 'specs.Питание' in result.missing_fields


@pytest.mark.parametrize('data', [
    {'name': 42}, {'name': 'A', 'specs': {'a': 12}},
    {'name': 'A', 'unexpected': 'x'}, {'name': 'A', 'specs': {' ': 'x'}},
    {'name': 'A', 'description': 'x' * 20001},
])
def test_invalid_input(data):
    with pytest.raises(ValidationError):
        ProductInput.model_validate(data)
