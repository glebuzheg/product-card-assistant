# Product Card Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Локальный сервис генерации достоверных черновиков карточек.
**Architecture:** Три небольших модуля: схемы, генерация и HTTP. Один OpenAI-клиент, без БД.
**Tech Stack:** Python 3.12, FastAPI, Pydantic, OpenAI SDK, uv, pytest, Ruff.
**Spec:** docs/design.md и openspec/changes/generate-product-card/specs/product-card-generation/spec.md.

## Global Constraints
- Заголовок ≤70 символов; описание 800–1200; 3–5 различных поисковых запросов.
- Одно исправление ответа; 45 секунд на вызов; тело запроса ≤64 KiB.
- Числа и характеристики только из входа. Нет ключей в Git.

## Review Focus
- Числа в названии не подтверждают технические параметры → тест model_number_is_not_spec.
- Поток без Content-Length превышает лимит → тест streamed_body_limit.
- Отказ/обрыв API не даёт успешный черновик → тест refusal_or_incomplete.
- Строки из пробелов не считаются данными → тест whitespace_input.
- Неизвестные поля/неверные типы не передаются модели → тест invalid_input.

### Task 1: Схемы и проверка фактов
Files: product_cards/schemas.py, product_cards/generation.py; tests/test_schemas.py, tests/test_generation.py.
Interfaces: ProductInput; Draft; CardResult; make_result(product, draft=None); validate_draft(product, draft).
- [ ] Написать тесты пропусков, strict-типов и границ длин; запустить и увидеть отказ из-за отсутствующей реализации.
- [ ] Реализовать схемы и проверки; uv run pytest tests/test_schemas.py tests/test_generation.py → PASS.
- [ ] Commit: feat: validate product data and grounded drafts.

### Task 2: Провайдер и HTTP
Files: product_cards/api.py, product_cards/generation.py; tests/test_api.py.
Interfaces: async generate_card(product, client, model) -> CardResult; FastAPI app.
- [ ] Написать HTTP-тесты с настоящим OpenAI SDK и MockTransport: корректный ответ, исправление, две ошибки, таймаут, 429, отказ, 422, 413, 503.
- [ ] Увидеть их FAIL, реализовать маршрут и обработку ошибок; uv run pytest → PASS.
- [ ] Commit: feat: expose OpenAI product card endpoint.

### Task 3: Примеры и сдача
Files: examples/*.json, examples/SOURCES.md, README.md, .github/workflows/checks.yml.
- [ ] Подготовить два проверенных входа и неполный пример, добавить проверку входных JSON.
- [ ] Запустить реальную генерацию при наличии ключа; сохранить только реальные выходы, проверить вручную.
- [ ] Проверить команды README, uv run pytest, uv run ruff check ., uv run ruff format --check ., openspec validate --all --strict.
- [ ] Независимое ревью, исправление существенных ошибок, commit и push в согласованный репозиторий.

## Execution
Реализация в текущем сеансе после согласования проектного документа; повторное согласование уже разрешённой реализации не требуется. Прогресс фиксируется в задачах OpenSpec.
