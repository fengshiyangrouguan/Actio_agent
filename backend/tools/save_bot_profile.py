from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import toml  # 用于读写 TOML 配置文件

from backend.common.config.config_service import ConfigService
from backend.mainsystem.base_tool import BaseTool, ToolExecutionContext


class SaveBotProfileTool(BaseTool):
    """保存机器人配置工具，将机器人姓名和性格存入配置文件并触发热重载"""

    @property
    def scopes(self) -> List[str]:
        """定义工具可用的模式，这里仅在 'setup' 模式下可用"""
        return ["setup"]

    @property
    def name(self) -> str:
        """工具名称"""
        return "save_bot_profile"

    @property
    def description(self) -> str:
        """工具描述（中文）"""
        return "将机器人姓名和性格配置保存到 bot 配置文件，并触发热重载。"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """定义工具参数的 JSON Schema"""
        return {
            "type": "object",
            "properties": {
                "bot_name": {"type": "string"},
                "bot_personality": {"type": "string"},
            },
            "required": ["bot_name", "bot_personality"], 
        }

    async def execute(self, context: ToolExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        """
        执行工具逻辑：
        1. 获取 bot_name 和 bot_personality 参数
        2. 写入 configs/bot_config.toml 文件
        3. 清理缓存以触发热重载
        """
        # 获取参数并去掉首尾空格
        bot_name = str(kwargs["bot_name"]).strip()
        bot_personality = str(kwargs["bot_personality"]).strip()

        # 配置目录
        config_dir = Path("configs")
        config_dir.mkdir(parents=True, exist_ok=True)  # 如果目录不存在则创建
        config_path = config_dir / "bot_config.toml"  # 配置文件路径

        # 新配置内容
        config_data: Dict[str, Any] = {
            "system": {
                "version": "0.1.0",
                "owner_id": None,
                "log_level": "INFO",
            },
            "persona": {
                "bot_name": bot_name,
                "bot_personality": bot_personality,
            }
        }

        # 如果已有配置文件，则读取并合并
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as file:
                existing = toml.load(file)
            existing.update(config_data)  # 合并新配置
            config_data = existing

        # 写入配置文件
        with open(config_path, "w", encoding="utf-8") as file:
            toml.dump(config_data, file)

        # 清理缓存，使系统重新加载最新配置
        ConfigService().clear_cache("bot")

        # 返回操作结果
        return {
            "saved": True,  # 保存成功
            "bot_name": bot_name,
            "bot_personality": bot_personality,
            "config_path": str(config_path),  # 返回文件路径
        }