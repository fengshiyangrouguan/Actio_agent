from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .agent import MainSystemAgent
from .planner import PlannerService
from .schemas import BotProfile, ChatRequest, SessionStateResponse, TaskStateResponse
from .store import InMemoryTaskStore
from .tool_manager import ToolManager

store = InMemoryTaskStore()
main_agent = MainSystemAgent(store)

app = FastAPI(title="Actio MainSystem API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    """
    检查服务健康状态。
    返回: {"status": "ok"} 表示服务运行正常。
    """
    return {"status": "ok"}


@app.get("/api/profile")
async def get_profile() -> dict[str, object]:
    """
    获取机器人运行时的配置信息。
    返回: 
        mode: 智能体当前模式 (如 'setup' 或 'main')
        bot_profile: 机器人的名字、性格等配置信息
    """
    mode, bot_profile = main_agent.get_runtime_state()
    return {"mode": mode, "bot_profile": bot_profile.model_dump()}


@app.post("/api/chat")
async def create_chat_task(payload: ChatRequest):
    """
    提交一个新的聊天请求。
    逻辑: 
        1. 接收用户输入。
        2. 在后台通过 Planner 规划并执行工具。
        3. 立即返回一个 Task 对象（包含 task_id），而不阻塞等待 AI 思考完成。
    """
    return await main_agent.submit(payload)


@app.get("/api/chat/{task_id}", response_model=TaskStateResponse)
async def get_chat_task(task_id: str):
    """
    查询指定聊天任务的快照状态。
    参数: task_id (创建聊天时返回的 ID)
    返回: 包含任务进度、已产生的更新记录等。
    报错: 如果任务 ID 不存在，抛出 404 异常。
    """
    try:
        return TaskStateResponse(task=store.get_task(task_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


@app.get("/api/sessions/{session_id}", response_model=SessionStateResponse)
async def get_session_state(session_id: str):
    """
    获取指定会话的历史记忆。
    参数: session_id
    返回: 该会话的内存窗口数据（用于模型理解上下文）。
    """
    return SessionStateResponse(
        session_id=session_id,
        memory_window=store.get_memory_window(session_id),
    )


@app.get("/api/chat/{task_id}/events")
async def stream_chat_events(task_id: str):
    """
    开启一个服务器发送事件 (SSE) 流，实时推送任务更新。
    逻辑:
        1. 首先推送该任务已经产生的历史更新。
        2. 保持长连接，实时推送后台产生的新更新（如：AI 思考中、调用工具 A、工具返回结果）。
        3. 当收到 'done' (完成) 或 'error' (错误) 事件时，自动断开连接。
    """
    try:
        task = store.get_task(task_id)
        queue = store.queue_for(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc

    async def event_stream():
        for update in task.updates:
            yield f"data: {update.model_dump_json()}\n\n"

        while True:
            update = await queue.get()
            yield f"data: {update.model_dump_json()}\n\n"
            if update.kind in {"done", "error"}:
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")
