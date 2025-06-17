import logging
from typing import Dict, Any
from datetime import datetime
import uuid

from core.models import UnifiedMessage, UnifiedResponse, ClientType, MessageType, AdapterStatus, WebMessage
from core.message_processor import MessageProcessor

logger = logging.getLogger(__name__)

class WebAdapter:
    """Адаптер для веб-интерфейса"""
    
    def __init__(self, message_processor: MessageProcessor):
        self.message_processor = message_processor
        self.status = AdapterStatus(is_healthy=False)
        self.active_sessions = {}
        
    async def initialize(self):
        """Инициализация веб-адаптера"""
        try:
            self.status.is_healthy = True
            logger.info("Web адаптер инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации Web адаптера: {e}")
            self.status.is_healthy = False
    
    async def shutdown(self):
        """Остановка веб-адаптера"""
        self.active_sessions.clear()
        logger.info("Web адаптер остановлен")
    
    async def handle_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка сообщения от веб-клиента"""
        try:
            if not self.status.is_healthy:
                return {"error": "Web адаптер не готов к работе"}
            
            # Валидация входных данных
            web_message = WebMessage(**message_data)
            
            # Создание унифицированного сообщения
            unified_message = UnifiedMessage(
                id=str(uuid.uuid4()),
                client_type=ClientType.WEB,
                message_type=web_message.message_type,
                content=web_message.content,
                user_id=web_message.user_id,
                timestamp=datetime.now(),
                metadata={
                    "session_id": web_message.session_id,
                    "user_agent": "web_client"  # Можно добавить из заголовков
                }
            )
            
            # Обработка через центральный процессор
            response = await self.message_processor.process_message(unified_message)
            
            # Обновление статистики
            self.status.last_activity = datetime.now()
            self.status.message_count += 1
            
            # Обновление сессии
            if web_message.session_id:
                self.active_sessions[web_message.session_id] = {
                    "user_id": web_message.user_id,
                    "last_activity": datetime.now()
                }
            
            return {
                "success": True,
                "response": {
                    "content": response.content,
                    "type": response.response_type,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка обработки веб-сообщения: {e}")
            self.status.error_count += 1
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """Получение статуса веб-интерфейса"""
        return {
            "healthy": self.status.is_healthy,
            "active_sessions": len(self.active_sessions),
            "last_activity": self.status.last_activity.isoformat() if self.status.last_activity else None,
            "message_count": self.status.message_count,
            "error_count": self.status.error_count,
            "sessions": {
                session_id: {
                    "user_id": session_data["user_id"],
                    "last_activity": session_data["last_activity"].isoformat()
                }
                for session_id, session_data in self.active_sessions.items()
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья адаптера"""
        return {
            "healthy": self.status.is_healthy,
            "last_activity": self.status.last_activity.isoformat() if self.status.last_activity else None,
            "message_count": self.status.message_count,
            "error_count": self.status.error_count,
            "active_sessions": len(self.active_sessions)
        }

