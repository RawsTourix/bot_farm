import logging
from typing import Dict, Any, List
from datetime import datetime
import uuid
import shlex

from core.models import UnifiedMessage, UnifiedResponse, ClientType, MessageType, AdapterStatus, CommandRequest
from core.message_processor import MessageProcessor

logger = logging.getLogger(__name__)

class CLIAdapter:
    """Адаптер для CLI интерфейса"""
    
    def __init__(self, message_processor: MessageProcessor):
        self.message_processor = message_processor
        self.status = AdapterStatus(is_healthy=False)
        self.available_commands = {
            "help": "Показать справку по командам",
            "status": "Показать статус системы",
            "stats": "Показать статистику Gateway",
            "send": "Отправить сообщение для обработки",
            "history": "Показать историю команд",
            "clear": "Очистить историю"
        }
        self.command_history = []
        
    async def initialize(self):
        """Инициализация CLI адаптера"""
        try:
            self.status.is_healthy = True
            logger.info("CLI адаптер инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации CLI адаптера: {e}")
            self.status.is_healthy = False
    
    async def shutdown(self):
        """Остановка CLI адаптера"""
        self.command_history.clear()
        logger.info("CLI адаптер остановлен")
    
    async def handle_command(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка CLI команды"""
        try:
            if not self.status.is_healthy:
                return {"error": "CLI адаптер не готов к работе"}
            
            # Валидация входных данных
            command_request = CommandRequest(**command_data)
            
            # Добавление в историю
            self.command_history.append({
                "command": command_request.command,
                "args": command_request.args,
                "timestamp": datetime.now(),
                "user_id": command_request.user_id
            })
            
            # Обработка встроенных команд
            if command_request.command in self.available_commands:
                result = await self._handle_builtin_command(command_request)
                return result
            
            # Создание унифицированного сообщения для обработки
            content = f"{command_request.command} {' '.join(command_request.args)}".strip()
            unified_message = UnifiedMessage(
                id=str(uuid.uuid4()),
                client_type=ClientType.CLI,
                message_type=MessageType.COMMAND,
                content=content,
                user_id=command_request.user_id,
                timestamp=datetime.now(),
                metadata={
                    "command": command_request.command,
                    "args": command_request.args,
                    "options": command_request.options
                }
            )
            
            # Обработка через центральный процессор
            response = await self.message_processor.process_message(unified_message)
            
            # Обновление статистики
            self.status.last_activity = datetime.now()
            self.status.message_count += 1
            
            return {
                "success": True,
                "output": response.content,
                "command": command_request.command,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка обработки CLI команды: {e}")
            self.status.error_count += 1
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _handle_builtin_command(self, command_request: CommandRequest) -> Dict[str, Any]:
        """Обработка встроенных CLI команд"""
        cmd = command_request.command
        
        if cmd == "help":
            return {
                "success": True,
                "output": self._format_help()
            }
        elif cmd == "status":
            stats = await self.message_processor.get_stats()
            return {
                "success": True,
                "output": self._format_status(stats)
            }
        elif cmd == "stats":
            stats = await self.message_processor.get_stats()
            return {
                "success": True,
                "output": self._format_stats(stats)
            }
        elif cmd == "history":
            return {
                "success": True,
                "output": self._format_history()
            }
        elif cmd == "clear":
            self.command_history.clear()
            return {
                "success": True,
                "output": "История команд очищена"
            }
        elif cmd == "send":
            if not command_request.args:
                return {
                    "success": False,
                    "error": "Использование: send <сообщение>"
                }
            
            message_text = " ".join(command_request.args)
            unified_message = UnifiedMessage(
                id=str(uuid.uuid4()),
                client_type=ClientType.CLI,
                message_type=MessageType.TEXT,
                content=message_text,
                user_id=command_request.user_id,
                timestamp=datetime.now(),
                metadata={"via_cli": True}
            )
            
            response = await self.message_processor.process_message(unified_message)
            return {
                "success": True,
                "output": response.content
            }
        
        return {
            "success": False,
            "error": f"Неизвестная команда: {cmd}"
        }
    
    def _format_help(self) -> str:
        """Форматирование справки"""
        help_text = "Доступные команды:\\n\\n"
        for cmd, desc in self.available_commands.items():
            help_text += f"  {cmd:<12} - {desc}\\n"
        
        help_text += "\\nПримеры использования:\\n"
        help_text += "  send Привет, как дела?\\n"
        help_text += "  status\\n"
        help_text += "  history\\n"
        
        return help_text
    
    def _format_status(self, stats: Dict[str, Any]) -> str:
        """Форматирование статуса"""
        uptime_hours = stats.get("uptime_seconds", 0) / 3600
        return f"""
Статус Gateway:
  Время работы: {uptime_hours:.1f} часов
  Всего сообщений: {stats.get("total_messages", 0)}
  Активных сессий: {stats.get("active_sessions", 0)}
  Ошибок: {stats.get("errors", 0)}
        """.strip()
    
    def _format_stats(self, stats: Dict[str, Any]) -> str:
        """Форматирование детальной статистики"""
        messages_by_client = stats.get("messages_by_client", {})
        return f"""
Детальная статистика Gateway:
  Общее количество сообщений: {stats.get("total_messages", 0)}
  
  По типам клиентов:
    Telegram: {messages_by_client.get("telegram", 0)}
    Web: {messages_by_client.get("web", 0)}  
    CLI: {messages_by_client.get("cli", 0)}
  
  Активных сессий: {stats.get("active_sessions", 0)}
  Ошибок: {stats.get("errors", 0)}
  Время работы: {stats.get("uptime_seconds", 0):.1f} секунд
        """.strip()
    
    def _format_history(self) -> str:
        """Форматирование истории команд"""
        if not self.command_history:
            return "История команд пуста"
        
        history_text = "История команд:\\n\\n"
        for i, entry in enumerate(self.command_history[-10:], 1):  # Последние 10 команд
            timestamp = entry["timestamp"].strftime("%H:%M:%S")
            cmd = entry["command"]
            args = " ".join(entry["args"]) if entry["args"] else ""
            history_text += f"  {i:2d}. [{timestamp}] {cmd} {args}\\n"
        
        return history_text
    
    async def get_help(self) -> Dict[str, Any]:
        """Получение справки по CLI"""
        return {
            "commands": self.available_commands,
            "usage": "Отправьте POST запрос на /cli/execute с JSON: {\"command\": \"<команда>\", \"args\": [\"<аргументы>\"], \"user_id\": \"<id>\"}",
            "examples": [
                {"command": "help", "args": [], "description": "Показать справку"},
                {"command": "send", "args": ["Привет", "мир"], "description": "Отправить сообщение"},
                {"command": "status", "args": [], "description": "Показать статус"}
            ]
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья адаптера"""
        return {
            "healthy": self.status.is_healthy,
            "last_activity": self.status.last_activity.isoformat() if self.status.last_activity else None,
            "message_count": self.status.message_count,
            "error_count": self.status.error_count,
            "command_history_size": len(self.command_history)
        }

