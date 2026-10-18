# Real-time Task Board

Backend на FastAPI для общей доски задач в реальном времени.

Функционал:
- регистрация пользователя;
- логин и получение JWT;
- получение текущего пользователя;
- создание задач;
- просмотр списка задач;
- получение задачи по id;
- обновление задачи;
- удаление задачи;
- фильтрация, поиск, сортировка и пагинация задач;
- websocket-уведомления об изменениях задач.

## Стек

- FastAPI
- PostgreSQL
- asyncpg
- JWT
- WebSocket

## Структура

```text
app/
├── api/
│   ├── endpoints/
│   │   ├── tasks.py
│   │   └── users.py
│   └── schemas/
│       ├── task.py
│       └── user.py
├── core/
│   ├── config.py
│   └── security.py
├── db/
│   └── database.py
main.py
```

