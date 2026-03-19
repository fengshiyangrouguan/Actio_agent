from __future__ import annotations
import json
from typing import Any, List

from backend.common.di.container import container
from backend.llm_api.factory import LLMRequestFactory
from .schemas import AgentMode, AgentPlan, BotProfile, MemoryMessage, ToolDefinition, PlannedAction
from backend.common.logger import get_logger
logger = get_logger("planner")

class PlannerService:
    def __init__(self) -> None:
        self.llm_factory = container.resolve(LLMRequestFactory)

    async def build_plan(
        self,
        user_input: str,
        tools: List[ToolDefinition],
        mode: AgentMode,
        skill_prompt: str,
        bot_profile: BotProfile,
        memory_window: List[MemoryMessage] | None = None,
    ) -> AgentPlan:
        """统一规划入口"""
        memory = memory_window or []
        
        # 1. 构造上下文
        tool_lines = json.dumps([t.model_dump() for t in tools], ensure_ascii=False, indent=2)
        memory_lines = "\n".join([f"- {m.role}: {m.content}" for m in memory])
        
        # 2. 根据模式构建不同的 Prompt
        if mode == "setup":
            bot_setting =''
        else:
            bot_setting = f"你叫 {bot_profile.bot_name or '助手'}，性格设定：{bot_profile.bot_personality or '专业且乐于助人'}。"
        
        prompt = self._get_main_prompt(user_input, tool_lines, memory_lines, skill_prompt, bot_setting)

        # 3. LLM 执行与解析
        try:
            # 使用你新代码里的 "planner" 标识获取请求对象
            request = self.llm_factory.get_request("planner")
            content, _ = await request.execute(prompt)
            logger.info(f"原始规划：{content}")
            return self._parse_json_plan(content, user_input)
        except Exception as e:
            # 兜底逻辑
            logger.error(f"LLM解析时发生错误:{e}")
            return AgentPlan(
                immediate_reply="收到，我先按当前信息继续处理。",
                execution_goal=user_input,
                actions=[],
            )

    def _get_main_prompt(self, user_input, tool_lines, memory_lines, skill_prompt, bot_setting:str) -> str:
        """参考新代码风格的中文编排 Prompt"""
        return f"""
{bot_setting}

## 近期记忆：
{memory_lines}

## 用户当前输入：
"{user_input}"

## 你当前激活的技能：
{skill_prompt}
## 可用工具选项：
{tool_lines}

## 输出要求：
1. 若需使用工具，请在 actions 列表中规划。你可以选择不调用工具。
2. immediate_reply 给出简短的人性化回复，如果有action的话，可以告诉用户接下来你要干什么。不要刻意描述出你的人格特性，不用自我介绍
3. 严格输出 JSON 格式。

{{
  "immediate_reply": "string",
  "execution_goal": "string",
  "actions": [
    {{ "action": "工具名", "parameters": {{}}, "rationale": "理由" }}
  ]
}}
""".strip()

    def _parse_json_plan(self, content: str, user_input: str) -> AgentPlan:
        """结构化解析逻辑 (借鉴 EnterQQAppTool 的解析方式)"""
        res_text = content.strip()
        if "```" in res_text:
            res_text = res_text.split("```json")[-1].split("```")[0].strip()
        
        data = json.loads(res_text)
        
        planned_actions = [
            PlannedAction(
                tool_name=item.get("action") or item.get("tool_name"),
                parameters=item.get("parameters", {}),
                rationale=item.get("rationale", "planner")
            ) for item in data.get("actions", []) if item.get("action") or item.get("tool_name")
        ]

        return AgentPlan(
            immediate_reply=data.get("immediate_reply", "收到。"),
            execution_goal=data.get("execution_goal", user_input),
            actions=planned_actions
        )
