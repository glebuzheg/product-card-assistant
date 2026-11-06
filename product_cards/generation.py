import re
from decimal import Decimal

from product_cards.schemas import Draft, ProductInput

NUMBER = re.compile(r'(?<!\w)[+−–-]?\d+(?:[.,]\d+)?')


def numbers(text: str) -> set[Decimal]:
    # shortcut: lexical numeric checks cannot prove meaning or units; review drafts before publishing.
    return {Decimal(n.replace(',', '.').replace('−', '-').replace('–', '-'))
            for n in NUMBER.findall(text)}


def validate_draft(product: ProductInput, draft: Draft) -> None:
    sources = {'name': product.name, 'manufacturer': product.manufacturer,
               'description': product.description,
               **{f'specs.{key}': value for key, value in product.specs.items()}}
    blocks = {'seo_title': draft.seo_title, 'seo_description': draft.seo_description,
              'commercial_block': draft.commercial_block,
              'search_queries': '\n'.join(draft.search_queries)}
    for evidence in draft.evidence:
        source = sources.get(evidence.source_field, '')
        if not source or evidence.source_quote not in source:
            raise ValueError('Неверная цитата источника')
        if evidence.claim not in blocks[evidence.block]:
            raise ValueError('Утверждение отсутствует в указанном блоке')
    allowed = numbers('\n'.join([product.description, *product.specs.values()]))
    for text in blocks.values():
        without_name = re.sub(re.escape(product.name), '', text, flags=re.IGNORECASE)
        if not numbers(without_name) <= allowed:
            raise ValueError('В тексте есть неподтверждённые числовые значения')
