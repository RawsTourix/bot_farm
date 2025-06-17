### Настройка телеграмм сервера для тестирования
1.  Создание туннеля для телеграмм сервера
```PowerShell
tuna http 8001
```
2.  В `.env` вставляем полученный адрес туннеля в переменную `WEBHOOK_DOMAIN`
3.  Запускаем `gateway.py` на `localhost:8000`
4.  Запускаем `servers/telegram/telegram_server.py`  на `localhost:8001`