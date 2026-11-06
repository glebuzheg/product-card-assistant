import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI
from starlette.types import ASGIApp, Receive, Scope, Send

from product_cards.generation import GenerationError, generate_card
from product_cards.schemas import CardResult, ProductInput


class BodyLimit:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        chunks = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > 65536:
                return await JSONResponse(
                    {"detail": "Тело запроса превышает 64 KiB"}, status_code=413
                )(scope, receive, send)
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        consumed = False

        async def buffered_receive():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, buffered_receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(".env")
    key = os.getenv("OPENAI_API_KEY", "").strip()
    app.state.model = os.getenv("OPENAI_MODEL", "").strip()
    app.state.llm = AsyncOpenAI(api_key=key, timeout=45.0, max_retries=0) if key else None
    try:
        yield
    finally:
        if app.state.llm is not None:
            await app.state.llm.close()


app = FastAPI(title="Product Card Assistant", version="0.1.0", lifespan=lifespan)
app.add_middleware(BodyLimit)


@app.exception_handler(RequestValidationError)
async def invalid_input(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Некорректный JSON или поля товара",
            "errors": [{"loc": list(e["loc"]), "type": e["type"]} for e in exc.errors()],
        },
    )


@app.exception_handler(GenerationError)
async def generation_error(request: Request, exc: GenerationError):
    return JSONResponse(status_code=exc.status, content={"detail": exc.message})


@app.post("/generate", response_model=CardResult)
async def generate(product: ProductInput, request: Request):
    """Создать черновик; неполные данные и отсутствующие характеристики отмечаются явно."""
    return await generate_card(product, request.app.state.llm, request.app.state.model)
