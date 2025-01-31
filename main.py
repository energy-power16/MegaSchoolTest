import time
from typing import List
import json
from fastapi import FastAPI, HTTPException, Request, Response
from openai import OpenAI
from pydantic import HttpUrl
from schemas.request import PredictionRequest, PredictionResponse
from utils.logger import setup_logger
import re
import os
from pydantic import BaseModel, HttpUrl
from typing import List
# Initialize
app = FastAPI()
logger = None


class PredictionResponse(BaseModel):
    id: int
    answer: int
    reasoning: str
    sources: List[HttpUrl]


@app.on_event("startup")
async def startup_event():
    global logger
    logger = await setup_logger()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    body = await request.body()
    await logger.info(
        f"Incoming request: {request.method} {request.url}\n"
        f"Request body: {body.decode()}"
    )

    response = await call_next(request)
    process_time = time.time() - start_time

    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk

    await logger.info(
        f"Request completed: {request.method} {request.url}\n"
        f"Status: {response.status_code}\n"
        f"Response body: {response_body.decode()}\n"
        f"Duration: {process_time:.3f}s"
    )

    return Response(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )


@app.post("/api/request", response_model=PredictionResponse)
async def predict(body: PredictionRequest):
    try:
        await logger.info(f"Processing prediction request with id: {body.id}")
        answer, reasoning, sources= await chat_with_vsegpt(body.query)  # Замените на реальный вызов модели

        response = PredictionResponse(
            id=body.id,
            answer=answer,
            reasoning=reasoning,
            sources=sources,
        )
        await logger.info(f"Successfully processed request {body.id}")
        return response
    except ValueError as e:
        error_msg = str(e)
        await logger.error(f"Validation error for request {body.id}: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        await logger.error(f"Internal error processing request {body.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


client = OpenAI(
    api_key= os.getenv('GPT_KEY'),
    base_url="https://api.vsegpt.ru/v1",
)
import re

def extract_json_values(text):
    """
    Извлекает значения полей answer, reasoning и sources из текста.
    """
    answer_match = re.search(r'"answer":\s*(\d+|null)', text)
    reasoning_match = re.search(r'"reasoning":\s*"([^"]+)"', text)
    sources_match = re.findall(r'"sources":\s*\[([^]]+)\]', text)

    answer = int(answer_match.group(1)) if answer_match and answer_match.group(1) != "null" else None
    reasoning = reasoning_match.group(1) if reasoning_match else None
    sources = sources_match[0].split(", ") if sources_match else []

    return {"answer": answer, "reasoning": reasoning, "sources": sources}




async def chat_with_vsegpt(request):

    promt = '''Ты — помощник, отвечающий на вопросы об Университете ИТМО.

- Отвечай кратко и только на русском языке.
- Если вопрос содержит варианты (числа от 1 до 10), укажи правильный номер. Если вариантов нет, верни null.
- Если нашёл источники, добавь их в ответ в формате ссылок. Если нет, оставь пустой список.
- **Не используй лишний текст. Твой ответ ДОЛЖЕН быть ЧИСТЫМ JSON.**
- **Не добавляй "json\n{" или ```json``` перед ответом. Просто верни JSON.**

Формат ответа:
{
  "answer": <число или null>,
  "reasoning": "<объяснение>",
}

Вопрос:
{question}


'''
    try:
        response = client.chat.completions.create(
            model="perplexity/latest-large-online",
            messages=[
                {'role': "system", 'content': promt},
                {'role': 'user', 'content': request}
            ],
            temperature=0.3,
            max_tokens=1000,
        )

        response_text = response.choices[0].message.content.strip()
        sources = response.citations[:3] if len(response.citations) > 3 else response.citations
        # Парсим JSON без лишних обработок
        response_json = extract_json_values(response_text)

        return response_json["answer"], response_json.get("reasoning", ''), sources
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Ответ модели не является валидным JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
