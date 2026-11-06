from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class ProductInput(StrictModel):
    name: Name
    manufacturer: Annotated[str, Field(max_length=200)] = ""
    specs: Annotated[dict[Name, Text], Field(max_length=100)] = Field(default_factory=dict)
    description: Annotated[str, Field(max_length=20000)] = ""

    @property
    def has_facts(self) -> bool:
        return bool(self.description or any(self.specs.values()))


class Evidence(StrictModel):
    block: Literal["seo_title", "seo_description", "search_queries", "commercial_block"]
    claim: Annotated[str, Field(min_length=1, max_length=1200)]
    source_field: Annotated[str, Field(min_length=1, max_length=210)]
    source_quote: Annotated[str, Field(min_length=1, max_length=20000)]


class Draft(StrictModel):
    seo_title: Annotated[str, Field(min_length=1, max_length=70)]
    seo_description: Annotated[str, Field(min_length=800, max_length=1200)]
    search_queries: Annotated[list[Name], Field(min_length=3, max_length=5)]
    commercial_block: Annotated[str, Field(min_length=1, max_length=1000)]
    evidence: Annotated[list[Evidence], Field(min_length=1, max_length=50)]

    @field_validator("search_queries")
    @classmethod
    def unique_queries(cls, values: list[str]) -> list[str]:
        if len({v.casefold() for v in values}) != len(values):
            raise ValueError("Поисковые запросы должны различаться")
        return values


class CardResult(StrictModel):
    status: Literal["ok", "needs_clarification"]
    seo_title: str | None = None
    seo_description: str | None = None
    characteristics: dict[str, str]
    search_queries: list[str] = Field(default_factory=list)
    commercial_block: str | None = None
    missing_fields: list[str]


def make_result(product: ProductInput, draft: Draft | None = None) -> CardResult:
    missing = [field for field in ("manufacturer", "description") if not getattr(product, field)]
    if not product.specs:
        missing.append("specs")
    missing.extend(f"specs.{key}" for key, value in product.specs.items() if not value)
    texts = draft.model_dump(exclude={"evidence"}) if draft else {}
    return CardResult(
        status="ok" if draft else "needs_clarification",
        characteristics={key: value or "данных нет" for key, value in product.specs.items()},
        missing_fields=missing,
        **texts,
    )
