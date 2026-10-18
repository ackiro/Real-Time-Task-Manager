import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.api.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.core.security import get_current_user, get_user_from_db, get_user_from_token
from app.db.database import get_db_connection

router = APIRouter(prefix="/tasks", tags=["Tasks"])


active_connections = []
ALLOWED_SORT_FIELDS = {
    "id": "id",
    "title": "title",
    "status": "status",
    "priority": "priority",
    "created_at": "created_at",
    "updated_at": "updated_at",
}


def serialize_task(task):
    data = dict(task)
    if data.get("created_at") is not None:
        data["created_at"] = data["created_at"].isoformat()
    if data.get("updated_at") is not None:
        data["updated_at"] = data["updated_at"].isoformat()
    return data


def to_task_read(task):
    return TaskRead(**dict(task))

@router.websocket("/ws")
async def websocket_tasks(ws: WebSocket):
    token = ws.query_params.get("token")
    if token is None:
        await ws.close(code=1008)
        return

    try:
        username = get_user_from_token(token)
    except HTTPException:
        await ws.close(code=1008)
        return

    async with ws.app.state.db.acquire() as db:
        user = await get_user_from_db(db, username)

    if user is None:
        await ws.close(code=1008)
        return

    await ws.accept()
    active_connections.append(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in active_connections:
            active_connections.remove(ws)

async def broadcast(message: dict):
    for connection in active_connections:
        await connection.send_json(message)


@router.get("/get")
async def list_tasks(
    db: asyncpg.Connection = Depends(get_db_connection),
    status: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    sort: str = "id",
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user = Depends(get_current_user),
):
    _ = current_user
    sort_direction = "ASC"
    sort_field = sort
    if sort.startswith("-"):
        sort_direction = "DESC"
        sort_field = sort[1:]

    if sort_field not in ALLOWED_SORT_FIELDS:
        raise HTTPException(status_code=400, detail="Invalid sort field")

    conditions = []
    params = []

    if status is not None:
        params.append(status)
        conditions.append(f"status = ${len(params)}")

    if priority is not None:
        params.append(priority)
        conditions.append(f"priority = ${len(params)}")

    if search is not None:
        params.append(f"%{search}%")
        conditions.append(
            f"(title ILIKE ${len(params)} OR description ILIKE ${len(params)})"
        )

    query = """
        SELECT *
        FROM tasks
    """

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += f" ORDER BY {ALLOWED_SORT_FIELDS[sort_field]} {sort_direction}"

    params.append(limit)
    query += f" LIMIT ${len(params)}"
    params.append(offset)
    query += f" OFFSET ${len(params)}"

    tasks = await db.fetch(query, *params)
    return [to_task_read(task) for task in tasks]

@router.get("/get/{id}")
async def get_task(
    id: int,
    db: asyncpg.Connection = Depends(get_db_connection),
    current_user = Depends(get_current_user),
):
    _ = current_user
    res =  await db.fetchrow(
        """
        SELECT *
        FROM tasks
        WHERE id = $1
        """, id
    )
    if res is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return to_task_read(res)

@router.post("/add")
async def create_task(
    task: TaskCreate,
    db: asyncpg.Connection = Depends(get_db_connection),
    current_user = Depends(get_current_user),
):
    res =  await db.fetchrow(
        """
        INSERT INTO tasks(title, description, owner_id)
        VALUES($1, $2, $3)
        RETURNING *
        """, task.title, task.description, current_user["id"]
    )
    if res is not None:
        await broadcast({
        "event": "task_created",
        "task": serialize_task(res)
        })
    return to_task_read(res)


@router.delete("/delete/{id}")
async def delete_task(
    id: int,
    db: asyncpg.Connection = Depends(get_db_connection),
    current_user = Depends(get_current_user),
):
    _ = current_user
    res =  await db.fetchrow(
        """
        DELETE
        FROM tasks
        WHERE id = $1
        RETURNING *
        """, id
    )
    if res is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await broadcast({
    "event": "task_deleted",
    "task": serialize_task(res)
    })
    return to_task_read(res)

@router.patch("/update/{id}")
async def update_task(
    id: int,
    task: TaskUpdate,
    db: asyncpg.Connection = Depends(get_db_connection),
    current_user = Depends(get_current_user),
):
    _ = current_user
    existing_task = await db.fetchrow(
        """
        SELECT *
        FROM tasks
        WHERE id = $1
        """,
        id,
    )
    if existing_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    title = task.title if task.title is not None else existing_task["title"]
    description = (
        task.description if task.description is not None else existing_task["description"]
    )
    status = task.status if task.status is not None else existing_task["status"]
    priority = (
        task.priority if task.priority is not None else existing_task["priority"]
    )
    res =  await db.fetchrow(
        """
        UPDATE tasks
        SET title = $1, description = $2, status = $3, priority = $4, updated_at = NOW()
        WHERE id = $5
        RETURNING *
        """, title, description, status, priority, id
    )
    if res is not None:
        await broadcast({
        "event": "task_updated",
        "task": serialize_task(res)
        })
    return to_task_read(res)
