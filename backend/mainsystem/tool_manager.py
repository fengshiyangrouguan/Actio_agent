from __future__ import annotations

import importlib
import inspect
import pkgutil
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from backend.mainsystem.base_tool import BaseTool, ToolExecutionContext

from .schemas import ToolDefinition

# 使用 slots 优化内存占用，存储已注册工具的实例
@dataclass(slots=True)
class RegisteredTool:
    instance: BaseTool  # 工具的具体实现类实例

    @property
    def definition(self) -> ToolDefinition:
        """
        将工具实例转换为前端或 LLM 规划器所需的元数据定义。
        包括：名称、描述、参数 JSON Schema 以及适用范围（Scopes）。
        """
        return ToolDefinition(
            name=self.instance.name,
            description=self.instance.description,
            parameters_schema=self.instance.parameters_schema,
            scopes=list(self.instance.scopes),
        )


class ToolManager:
    """
    工具管理类：负责动态加载工具、根据当前模式筛选工具并调度执行。
    """
    def __init__(self) -> None:
        self._tools: Dict[str, RegisteredTool] = {}

    def register_tool(self, tool: BaseTool) -> None:
        """手动注册一个工具实例"""
        self._tools[tool.name] = RegisteredTool(instance=tool)

    def load_from_package(self, package_name: str) -> None:
        """
        动态扫描机制：从指定的 Python 包中自动发现并加载所有 BaseTool 的子类。
        """
        # 导入工具所在的包
        package = importlib.import_module(package_name)
        package_path = getattr(package, "__path__", None)
        if package_path is None:
            return

        # 遍历包下的所有模块
        for module_info in pkgutil.iter_modules(package_path):
            # 忽略以 _ 开头的私有模块
            if module_info.name.startswith("_"):
                continue

            # 动态导入子模块
            module = importlib.import_module(f"{package_name}.{module_info.name}")
            
            # 检查模块中定义的所有类
            for _, obj in inspect.getmembers(module, inspect.isclass):
                # 筛选条件：必须是 BaseTool 的子类，且不是 BaseTool 本身
                if obj is BaseTool or not issubclass(obj, BaseTool):
                    continue
                # 排除抽象基类（不能实例化的类）
                if inspect.isabstract(obj):
                    continue
                
                # 实例化工具并注册
                self.register_tool(obj())

    def list_definitions(self, scopes: Optional[Iterable[str]] = None) -> List[ToolDefinition]:
        """
        获取可用工具的列表。
        :param scopes: 可选，传入当前模式（如 ['setup'] 或 ['main']）。
                       如果传入，则只返回支持该作用域的工具。
        """
        # 如果未指定作用域，返回全部工具定义
        if scopes is None:
            return [tool.definition for tool in self._tools.values()]

        scope_set = set(scopes)
        # 筛选逻辑：工具的作用域为空（全局可用）或者工具作用域与传入的作用域有交集
        return [
            tool.definition
            for tool in self._tools.values()
            if not tool.instance.scopes or scope_set.intersection(tool.instance.scopes)
        ]

    async def execute(
        self,
        name: str,
        parameters: Dict[str, Any],
        context: ToolExecutionContext,
    ) -> Dict[str, Any]:
        """
        执行指定的工具。
        :param name: 工具名称
        :param parameters: 由 LLM 规划器生成的参数字典
        :param context: 包含 task_id, session_id 等信息的运行时上下文
        :return: 工具执行结果（统一封装为字典格式）
        """
        # 查找工具
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"未找到名为 '{name}' 的已注册工具。")
        
        # 调用工具实例的异步执行方法，并将上下文和解包后的参数传入
        result = await tool.instance.execute(context=context, **parameters)
        
        # 确保返回结果始终是字典格式，方便后端处理和前端展示
        if isinstance(result, dict):
            return result
        return {"result": result}