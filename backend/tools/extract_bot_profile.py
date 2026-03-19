from __future__ import annotations
import json

from typing import Any, Dict, List
from backend.common.di.container import container
from backend.llm_api.factory import LLMRequestFactory
from backend.mainsystem.base_tool import BaseTool, ToolExecutionContext

class ExtractBotProfileTool(BaseTool):
    """从用户输入中提取机器人姓名和性格的 LLM 工具"""

    def __init__(self) -> None:
        self.llm_factory = None

    @property
    def scopes(self) -> List[str]:
        """仅在初始化引导模式下可用"""
        return ["setup"]

    @property
    def name(self) -> str:
        return "extract_bot_profile"

    @property
    def description(self) -> str:
        return "从用户的对话内容或当前输入中，分析并提取出用户想要设定的机器人名字和性格特征。"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """该工具不需要外部参数，它直接分析上下文"""
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string", 
                    "description": "需要分析的文本（通常是当前的 user_input）"
                }
            },
            "required": ["text"]
        }

    async def execute(self, context: ToolExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        """
        执行逻辑：
        1. 获取待分析文本
        2. 构造 Prompt 请求 LLM 进行结构化提取
        3. 返回提取结果
        """
        text_to_analyze = kwargs.get("text", context.user_input)

        # 构造给 LLM 的指令
        prompt = f"""
你是一个信息提取专家。请从以下用户的输入中提取出他们想为机器人设定的“名字”和“性格”。

## 用户输入：
"{text_to_analyze}"

## 输出要求：
1. 必须输出 JSON 格式。
2. 如果用户没提到名字或性格，对应的字段请返回空字符串 ""。
3. 名字字数控制在10字以内。

输出示例：
{{
  "bot_name": "名字",
  "bot_personality": "性格描述"
}}
""".strip()

        try:
            # 使用 "planner" 或专门的 "extractor" 配置
            self.llm_factory = container.resolve(LLMRequestFactory)
            request = self.llm_factory.get_request("planner")
            content, _ = await request.execute(prompt)
            
            # 清洗并解析 JSON
            res_text = content.strip()
            if "```" in res_text:
                res_text = res_text.split("```json")[-1].split("```")[0].strip()
            
            data = json.loads(res_text)
            
            return {
                "extracted": True,
                "bot_name": data.get("bot_name", "").strip(),
                "bot_personality": data.get("bot_personality", "").strip()
            }
        except Exception as e:
            return {
                "extracted": False,
                "error": f"提取失败: {str(e)}",
                "bot_name": "",
                "bot_personality": ""
            }