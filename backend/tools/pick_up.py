from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import logging

import toml

from backend.common.config.config_service import ConfigService
from backend.common.di.container import container
from backend.mainsystem.base_tool import BaseTool, ToolExecutionContext
from backend.mainsystem.inference_runner import InferenceRunner

logger = logging.getLogger(__name__)


class PickUpTool(BaseTool):
    """控制机械臂抓取指定商品的工具"""

    @property
    def scopes(self) -> List[str]:
        return ["main"]

    @property
    def name(self) -> str:
        return "pick_up"

    @property
    def description(self) -> str:
        return "危险操作：机械臂物理抓取。必须传入商品的target_id"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target_id": {"type": "string", "description": "商品唯一 ID"},
            },
            "required": ["target_id"]
        }

    async def execute(self, context: ToolExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        """
        执行抓取操作
        
        Args:
            context: 执行上下文
            **kwargs: 参数，包含 target_id
            
        Returns:
            抓取结果字典
        """
        # 获取目标ID
        target_id = kwargs.get("target_id")
        
        if not target_id:
            logger.error("缺少 target_id 参数")
            return {
                "status": "error",
                "success": False,
                "message": "缺少商品ID参数",
                "item_grabbed": None,
                "safety_check": "失败"
            }
        
        logger.info(f"开始抓取商品: {target_id}")
        
        try:
            # 从容器获取 InferenceRunner 实例
            runner = container.resolve(InferenceRunner)
            
            # 异步等待推理完成
            # run 方法内部会自动添加 .ckpt 后缀
            result = await runner.run(target_id)
            
            # 根据推理结果判断抓取状态
            # TODO： 当前pickup和send_to_cus是合并的，以后可考虑拆分
            if result.get("success"):
                status = "success"
                message = f"已成功抓取商品并交给客户 {target_id}"
                safety_check = "通过"
                item_grabbed = target_id
            elif result.get("status") == "safety_stop":
                status = "safety_stop"
                message = f"安全停止：{result.get('message', '检测到危险动作')}"
                safety_check = "失败 - 安全保护触发"
                item_grabbed = None
            elif result.get("status") == "model_not_found":
                status = "error"
                message = f"模型文件不存在：{result.get('message', '请检查模型文件')}"
                safety_check = "失败 - 模型缺失"
                item_grabbed = None
            elif result.get("status") == "camera_timeout":
                status = "error"
                message = "摄像头初始化超时，请检查摄像头连接"
                safety_check = "失败 - 硬件错误"
                item_grabbed = None
            elif result.get("status") == "move_failed":
                status = "error"
                message = "机械臂移动到起始位置失败"
                safety_check = "失败 - 运动异常"
                item_grabbed = None
            else:
                status = result.get("status", "unknown")
                message = result.get("message", f"抓取商品 {target_id} 失败")
                safety_check = "失败"
                item_grabbed = None
            
            logger.info(f"抓取完成 - 商品: {target_id}, 状态: {status}")
            
            # 返回结果
            return {
                "status": status,
                "item_grabbed": item_grabbed,
                "safety_check": safety_check,
                "success": bool(result.get("success")),
                "steps_executed": result.get("steps_executed", 0),
                "message": message,
                "model_name": result.get("model_name"),
                "target_id": target_id,
                "model_path": result.get("model_path")
            }
            
        except Exception as e:
            logger.exception(f"抓取商品 {target_id} 时发生异常: {e}")
            return {
                "status": "error",
                "success": False,
                "message": f"抓取执行失败：{str(e)}",
                "item_grabbed": None,
                "safety_check": "失败 - 系统异常",
                "target_id": target_id
            }