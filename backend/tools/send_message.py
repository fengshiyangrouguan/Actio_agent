from __future__ import annotations

from typing import Any, Dict, List

from backend.mainsystem.base_tool import BaseTool, ToolExecutionContext


class SendMessageTool(BaseTool):
    """发送文本消息工具，支持向指定用户或频道发送文本内容"""

    @property
    def scopes(self) -> List[str]:
        return ["main", "setup"]

    @property
    def name(self) -> str:
        """工具名称"""
        return "send_message"

    @property
    def description(self) -> str:
        """工具描述"""
        return "根据你的性格，发送一段文本消息。视情况而定提供一个简洁或详细、自然日常且口语化回复，除了换行符不要输出其他markdown标记"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """定义工具参数的 JSON Schema"""
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string", 
                    "description": "要发送的文本内容"
                },
            },
            "required": ["content"],
        }

    async def execute(self, context: ToolExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        """
        执行发送逻辑：
        1. 提取 target_id 和 content
        2. 调用底层通信服务（此处为模拟逻辑）
        3. 返回发送状态和元数据
        """
        # 1. 解析参数
        content = str(kwargs["content"]).strip()

        # 校验内容是否为空
        if not content:
            return {"success": False, "error": "消息内容不能为空"}


        # 3. 返回操作结果
        return {
            "success": True,
            "content": content,
            }