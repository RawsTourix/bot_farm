from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import asyncio
from datetime import datetime
import os

from adapters.telegram_adapter import TelegramAdapter
from adapters.web_adapter import WebAdapter
from adapters.cli_adapter import CLIAdapter
from core.message_processor import MessageProcessor
from core.models import UnifiedMessage, ClientType

from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Key Authentication
from fastapi.security import APIKeyHeader

# Настройка заголовка API ключей
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

# Получение API ключей из переменных среды
def get_api_keys():
    """Возвращает список валидных API-ключей"""
    keys = []
    
    # Ключ для Telegram
    if telegram_key := os.getenv("TELEGRAM_API_KEY"):
        keys.append(telegram_key)
    
    # Другие ключи (пример для веб и CLI)
    if web_key := os.getenv("WEB_API_KEY"):
        keys.append(web_key)
    
    if cli_key := os.getenv("CLI_API_KEY"):
        keys.append(cli_key)
    
    if not keys:
        raise RuntimeError("No API keys configured in environment variables")
    
    return keys

# Инициализация API ключей при старте приложения
VALID_API_KEYS = get_api_keys()

# Функция для проверки аутентификации
async def api_key_auth(api_key: str = Depends(API_KEY_HEADER)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key"
        )
    
    if api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )
    
    return api_key

# Инициализация компонентов
message_processor = MessageProcessor()
telegram_adapter = TelegramAdapter(message_processor)
web_adapter = WebAdapter(message_processor)
cli_adapter = CLIAdapter(message_processor)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Асинхронное управление жизненным циклом"""
    logger.info("Запуск Multi-Protocol Gateway...")
    await asyncio.gather(
        telegram_adapter.initialize(),
        web_adapter.initialize(),
        cli_adapter.initialize()
    )
    logger.info("Gateway успешно запущен")
    
    yield
    
    logger.info("Остановка Gateway...")
    await asyncio.gather(
        telegram_adapter.shutdown(),
        web_adapter.shutdown(),
        cli_adapter.shutdown()
    )

# CORS configuration
origins = os.getenv("CORS_ORIGINS", "*").split(",")

app = FastAPI(
    title="Multi-Protocol Gateway", 
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# === UNIFIED MESSAGE ENDPOINT ===

@app.post("/message", dependencies=[Depends(api_key_auth)])
async def unified_message_handler(message: UnifiedMessage):
    """Единый эндпоинт для всех типов сообщений"""
    try:
        processor = {
            ClientType.TELEGRAM: telegram_adapter.handle_unified_message,
            ClientType.WEB: web_adapter.handle_message,
            ClientType.CLI: cli_adapter.handle_command
        }[message.client_type]
        
        response = await processor(message)
        return {"status": "ok", "response": response.content}
    except KeyError:
        raise HTTPException(status_code=400, detail="Unsupported client type")
    except Exception as e:
        logger.exception(f"Ошибка обработки сообщения: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# === HEALTH AND STATUS ENDPOINTS ===

@app.get("/health")
async def health_check():
    """Проверка здоровья Gateway"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "adapters": {
            "telegram": await telegram_adapter.health_check(),
            "web": await web_adapter.health_check(),
            "cli": await cli_adapter.health_check(),
        }
    }

@app.get("/stats")
async def get_stats():
    """Статистика Gateway"""
    return await message_processor.get_stats()

@app.get("/")
async def root():
    return {"service": "Multi-Protocol Gateway", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)