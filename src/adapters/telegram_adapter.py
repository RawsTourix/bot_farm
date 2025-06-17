import logging
from typing import Dict, Any
from datetime import datetime
import uuid
import httpx

from core.models import UnifiedMessage, UnifiedResponse, ClientType, MessageType, AdapterStatus
from core.message_processor import MessageProcessor

logger = logging.getLogger(__name__)

class TelegramAdapter:
    """Адаптер для Telegram Bot API"""
    
    def __init__(self, message_processor: MessageProcessor):
        self.message_processor = message_processor
        self.status = AdapterStatus(is_healthy=False)
        
    async def initialize(self):
        """Инициализация Telegram адаптера"""
        try:
            self.status.is_healthy = True
            logger.info("Telegram адаптер инициализирован")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации Telegram адаптера: {e}")
            self.status.is_healthy = False
    
    async def shutdown(self):
        """Остановка Telegram адаптера"""
        logger.info("Telegram адаптер остановлен")
    
    async def handle_unified_message(self, message: UnifiedMessage) -> UnifiedResponse:
        """Обработка унифицированного сообщения от Telegram-сервера"""
        try:
            if not self.status.is_healthy:
                logger.warning("Telegram адаптер не готов к работе")
                return UnifiedResponse(
                    message_id=message.id,
                    client_type=message.client_type,
                    content="Telegram адаптер не готов к работе",
                    response_type=MessageType.TEXT
                )
            
            # Обработка через центральный процессор
            response = await self.message_processor.process_message(message)
            
            self.status.last_activity = datetime.now()
            self.status.message_count += 1
            
            return response
            
        except Exception as e:
            logger.error(f"Ошибка обработки унифицированного сообщения от Telegram-сервера: {e}")
            self.status.error_count += 1
            
            return UnifiedResponse(
                message_id=message.id,
                client_type=message.client_type,
                content=f"Произошла ошибка при обработке сообщения: {str(e)}",
                response_type=MessageType.TEXT
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья адаптера"""
        return {
            "healthy": self.status.is_healthy,
            "last_activity": self.status.last_activity.isoformat() if self.status.last_activity else None,
            "message_count": self.status.message_count,
            "error_count": self.status.error_count
        }