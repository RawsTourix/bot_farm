import logging
from typing import Dict, Any
from datetime import datetime
import asyncio

from .models import UnifiedMessage, UnifiedResponse, ClientType, MessageType

logger = logging.getLogger(__name__)

class MessageProcessor:
    """Центральный процессор сообщений"""
    
    def __init__(self):
        self.stats = {
            "total_messages": 0,
            "messages_by_client": {client.value: 0 for client in ClientType},
            "errors": 0,
            "start_time": datetime.now()
        }
        self.active_sessions = {}
        
    async def process_message(self, message: UnifiedMessage) -> UnifiedResponse:
        """Обработка унифицированного сообщения"""
        try:
            logger.info(f"Обработка сообщения от {message.client_type}: {message.content[:50]}...")
            
            # Обновление статистики
            self.stats["total_messages"] += 1
            self.stats["messages_by_client"][message.client_type] += 1
            
            # Здесь будет логика обработки сообщения
            # В реальном проекте здесь будет интеграция с MCP-клиентом и LLM
            response_content = await self._generate_response(message)
            
            response = UnifiedResponse(
                message_id=message.id,
                client_type=message.client_type,
                content=response_content,
                response_type=MessageType.TEXT
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            self.stats["errors"] += 1
            
            return UnifiedResponse(
                message_id=message.id,
                client_type=message.client_type,
                content=f"Произошла ошибка при обработке сообщения: {str(e)}",
                response_type=MessageType.TEXT
            )
    
    async def _generate_response(self, message: UnifiedMessage) -> str:
        """Генерация ответа на сообщение"""
        # Заглушка для демонстрации
        # В реальном проекте здесь будет вызов MCP-клиента и LLM
        
        if message.message_type == MessageType.COMMAND:
            return await self._handle_command(message)
        elif message.content.lower().startswith("/help"):
            return self._get_help_text()
        elif message.content.lower().startswith("/status"):
            return await self._get_status_text()
        else:
            return f"Получено сообщение: {message.content}\\n\\nЭто демо-ответ от Gateway. В реальном проекте здесь будет ответ от LLM через MCP."
    
    async def _handle_command(self, message: UnifiedMessage) -> str:
        """Обработка команд"""
        command = message.content.strip()
        
        if command == "/start":
            return f"Привет, {message.user_name or message.user_id}! Я Gateway бот, который объединяет CLI, Web и Telegram интерфейсы."
        elif command == "/stats":
            return await self._get_status_text()
        else:
            return f"Неизвестная команда: {command}"
    
    def _get_help_text(self) -> str:
        """Справочная информация"""
        return """
Доступные команды:
/help - показать эту справку
/start - приветствие
/status - статус системы
/stats - статистика Gateway

Вы можете отправлять любые текстовые сообщения для обработки.
        """.strip()
    
    async def _get_status_text(self) -> str:
        """Информация о статусе"""
        uptime = datetime.now() - self.stats["start_time"]
        return f"""
Статус Gateway:
• Время работы: {uptime}
• Всего сообщений: {self.stats['total_messages']}
• Ошибок: {self.stats['errors']}
• Сообщений по типам:
  - Telegram: {self.stats['messages_by_client']['telegram']}
  - Web: {self.stats['messages_by_client']['web']}
  - CLI: {self.stats['messages_by_client']['cli']}
        """.strip()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        uptime = datetime.now() - self.stats["start_time"]
        return {
            **self.stats,
            "uptime_seconds": uptime.total_seconds(),
            "active_sessions": len(self.active_sessions)
        }