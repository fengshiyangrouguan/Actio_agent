from __future__ import annotations
import asyncio
import json
from pathlib import Path
from uuid import uuid4
from typing import List, Optional

from backend.common.config.config_service import ConfigService
from backend.common.di.container import container
from backend.llm_api.factory import LLMRequestFactory
from backend.common.config.schemas.bot_config import BotConfig
from backend.common.config.schemas.llm_api_config import LLMApiConfig
from backend.mainsystem.base_tool import ToolExecutionContext
from .schemas import AgentMode, BotProfile, AgentTask, ChatAcceptedResponse, ChatRequest, TaskUpdate, AgentPlan
from .store import InMemoryTaskStore
from .planner import PlannerService
from .tool_manager import ToolManager
from backend.common.logger import get_logger
logger = get_logger("agent")

class MainSystemAgent:
    def __init__(self, store: InMemoryTaskStore) -> None:
        self.store = store
        # 基础服务初始化与单例注册
        self.config_service = ConfigService()
        self.llm_factory = LLMRequestFactory()
        
        llm_api_config = self.config_service.get_config("llm_api")
        container.register_instance(LLMRequestFactory, self.llm_factory)
        container.register_instance(ConfigService, self.config_service)
        container.register_instance(LLMApiConfig, llm_api_config)

        # 工具与规划器加载
        self.tool_manager = ToolManager()
        self.tool_manager.load_from_package("backend.tools")
        self._skill_dir = Path(__file__).resolve().parent / "skills"
        self.planner = PlannerService()

        # 运行时状态：初始化为 setup 模式
        self.mode: AgentMode = "setup"
        self.bot_profile: Optional[BotProfile] = None

    def _resolve_mode_and_profile(self) -> BotProfile:
        """从配置中动态解析当前机器人身份及模式"""
        try:
            config: BotConfig = self.config_service.get_config("bot")
            if not config or not config.persona.bot_name.strip():
                self.mode = "setup"
                return BotProfile(bot_name="", bot_personality="")
            
            self.mode = "main"
            self.bot_profile = BotProfile(
                bot_name=config.persona.bot_name,
                bot_personality=config.persona.bot_personality
            )
            return self.bot_profile
        except Exception:
            self.mode = "setup"
            return BotProfile(bot_name="", bot_personality="")

    async def _generate_thought_response(self, stage: str, task: AgentTask, current_results: list = None) -> str:
        """
        [核心] 让 LLM 根据当前执行阶段生成拟人化的反馈。
        stage 可选: 'execute_start' (开始执行), 'tool_feedback' (工具反馈), 'final_summary' (最终总结)
        """
        if self.mode == "setup":
            bot_setting = "你现在没有身份，还在引导用户身份设定阶段"
        else:
            profile = self.bot_profile or BotProfile(bot_name="助手", bot_personality="专业且友好")
            bot_setting = f"你现在的身份是 {profile.bot_name}，性格设定为：{profile.bot_personality}。"
        
        memory = self.store.get_memory_window(task.session_id)
        
        prompt = f"""
{bot_setting}
        
当前任务目标：{task.plan.execution_goal}
当前阶段：{stage}
最近执行结果：{json.dumps(current_results, ensure_ascii=False) if current_results else "尚未开始执行具体动作"}

任务指令：
1. 请根据你的性格，给用户提供一个简洁、自然日常且口语化的任务执行反馈。让用户理解你刚刚完成了什么，平淡一些，尽量简短一些。
- 不描述动作（例如不要写“我摇了摇头”等）
- 不要重复你之前说过的话
2. 如果是 final_summary 阶段，请确认任务是否达成，并自然地结束对话。
3. 严禁输出 JSON，直接输出回复正文。
4. 保持角色代入感，不要说“我是 AI”之类的话。
""".strip()

        try:
            request = self.llm_factory.get_request("planner")
            content, _ = await request.execute(prompt)
            return content.strip()
        except Exception:
            return "处理完成。" if stage == "final_summary" else "正在继续..."
    async def submit(self, payload: ChatRequest) -> ChatAcceptedResponse:
        """接收请求入口：增加了静默决策逻辑"""
        task_id = str(uuid4())
        session_id = payload.session_id or task_id
        
        bot_profile = self._resolve_mode_and_profile()
        self.store.append_memory(session_id, "user", payload.message)
        
        # 1. 规划
        plan = await self.planner.build_plan(
            user_input=payload.message,
            tools=self.tool_manager.list_definitions(scopes=[self.mode]),
            mode=self.mode,
            skill_prompt=self._load_skill_prompt(self.mode),
            bot_profile=bot_profile,
            memory_window=self.store.get_memory_window(session_id),
        )
        
        # --- 优化策略 A: 如果没有任何动作 (Actions)，则视为普通对话 ---
        
        task = AgentTask(
            task_id=task_id, session_id=session_id, mode=self.mode,
            user_input=payload.message, status="queued",
            immediate_reply=plan.immediate_reply, plan=plan
        )
        self.store.create_task(task)
        await self.store.publish(task_id, TaskUpdate(kind="ack", message=plan.immediate_reply))

        if not plan.actions:
            # 存入记忆
            self.store.append_memory(session_id, "assistant", plan.immediate_reply)
            # 直接发送 done，因为这种任务没有中间过程
            await self.store.publish(task_id, TaskUpdate(
                kind="done", 
                message=plan.immediate_reply,
                metadata={"profile": bot_profile.model_dump()}
            ))

            return ChatAcceptedResponse(
                task_id=task_id, session_id=session_id, 
                reply=plan.immediate_reply, # 这就是最终回复
                mode=self.mode, bot_profile=bot_profile,
                status="accepted" 
            )

        asyncio.create_task(self._run(task_id, plan))

        return ChatAcceptedResponse(
            task_id=task_id, session_id=session_id, 
            reply=plan.immediate_reply, mode=self.mode, bot_profile=bot_profile
        )
    async def _run(self, task_id: str, plan: AgentPlan) -> None:
        """
        后台异步执行流：实现多阶段动态反馈与状态同步。
        优化点：
        1. 动作梳理：根据 actions 数量决定是否发送 execute_start。
        2. 结果包装：统一使用 ToolResult (假设 result 存入 metadata)。
        3. 身份刷新：执行保存配置后立即重载 profile。
        """
        task = self.store.get_task(task_id)
        if not task:
            return

        tool_outputs = []
        # 获取初始身份
        current_profile = self._resolve_mode_and_profile()

        # 构造初始工具执行上下文
        tool_ctx = ToolExecutionContext(
            task_id=task.task_id,
            session_id=task.session_id,
            user_input=task.user_input,
            mode=task.mode,
            bot_profile=current_profile.model_dump(),
            memory_window=[{"role": m.role, "content": m.content} for m in self.store.get_memory_window(task.session_id)]
        )

        task.status = "running"

        # --- 优化策略：如果动作多于1个，才发送“准备开始”的反馈，避免单步任务太啰嗦 ---
        # if len(plan.actions) > 1:
        #     start_msg = await self._generate_thought_response("execute_start", task)
        #     await self.store.publish(task_id, TaskUpdate(kind="plan", message=start_msg))

        try:
            # 遍历所有动作，同时获取索引以判断是否为最后一个
            for idx, action in enumerate(plan.actions):
                # 1. 执行具体工具
                # 注意：假设你的 tool_manager.execute 返回的是 ToolResult 对象
                result = await self.tool_manager.execute(action.tool_name, action.parameters, tool_ctx)
                
                # 记录结果快照
                result_dict = result if isinstance(result, dict) else {"result": result}
                # 准备发送给前端的元数据
                event_metadata = {"result": result_dict}
                current_action_summary = {"action": action.tool_name, "result": result_dict}
                tool_outputs.append(current_action_summary)

                # 2. 特殊逻辑：如果是保存配置工具，强制刷新系统和缓存
                if action.tool_name == "save_bot_profile" and result_dict.get("success", result_dict.get("saved", True)):
                    self.config_service.clear_cache("bot")
                    # 关键：刷新 Agent 内部的 mode 和 bot_profile 成员变量
                    refreshed_profile = self._resolve_mode_and_profile() 
                    
                    # 更新后续工具可见的上下文
                    tool_ctx.bot_profile = refreshed_profile.model_dump()
                    tool_ctx.mode = self.mode
                    
                    # 告知前端模式已切换（如果有需要）
                    event_metadata["bot_profile"] = refreshed_profile.model_dump()
                    event_metadata["new_mode"] = self.mode

                # 只有非最后一个 action 才发送 tool_feedback
                if idx < len(plan.actions) - 1:
                    # 3. [动态节点] 每一个动作完成后的拟人化反馈
                    # LLM 会看到刚才 result 里的 summary 或 error
                    progress_msg = await self._generate_thought_response("tool_feedback", task, current_results=[current_action_summary])
                    
                    await self.store.publish(task_id, TaskUpdate(
                        kind="tool", 
                        message=progress_msg, 
                        metadata=event_metadata
                    ))

                # 如果工具明确返回失败，且你希望中断后续流程：
                if not result_dict.get("success", result_dict.get("saved", True)):
                    # 可以选择在这里 raise Exception 或者 break
                    logger.warning(f"Task {task_id} interrupted: Tool {action.tool_name} failed.")
                    break   # 中断循环，但后续仍会执行 final_summary（可根据需要调整）

            # --- 4. [动态节点] 全部任务完成后的总结回复 ---
            # 此时的 _generate_thought_response 会使用 self.bot_profile（可能是刚更新过的）
            final_msg = await self._generate_thought_response("final_summary", task, tool_outputs)
            
            # 更新任务最终状态
            task.status = "completed"
            task.final_message = final_msg
            
            # 将最终总结存入对话记忆，维持上下文
            self.store.append_memory(task.session_id, "assistant", final_msg)
            
            # 发布完成事件
            await self.store.publish(task_id, TaskUpdate(kind="done", message=final_msg))

        except Exception as e:
            logger.error(f"Error executing task {task_id}: {str(e)}")
            task.status = "failed"
            error_feedback = f"抱歉，处理过程中遇到了点问题：{str(e)}"
            await self.store.publish(task_id, TaskUpdate(kind="error", message=error_feedback))
    def _load_skill_prompt(self, mode: AgentMode) -> str:
        path = self._skill_dir / ("setup/SKILL.md" if mode == "setup" else "main/SKILL.md")
        return path.read_text(encoding="utf-8") if path.exists() else "尽力协助用户。"

    def get_runtime_state(self) -> tuple[AgentMode, BotProfile]:
        return self.mode, self._resolve_mode_and_profile()
