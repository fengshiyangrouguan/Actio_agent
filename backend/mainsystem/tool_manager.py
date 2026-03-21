from __future__ import annotations

import importlib
import inspect
import pkgutil
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from backend.common.logger import get_logger
from backend.mainsystem.base_tool import BaseTool, ToolExecutionContext

from .schemas import ToolDefinition

logger = get_logger("tool_manager")


@dataclass
class RegisteredTool:
    instance: BaseTool

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.instance.name,
            description=self.instance.description,
            parameters_schema=self.instance.parameters_schema,
            scopes=list(self.instance.scopes),
        )


class ToolManager:
    """
    工具管理类：负责自动发现、注册、筛选和执行工具。
    """

    def __init__(self) -> None:
        self._tools: Dict[str, RegisteredTool] = {}

    def register_tool(self, tool: BaseTool) -> None:
        """手动注册一个工具实例。"""
        if tool.name in self._tools:
            logger.warning(
                f"Tool '{tool.name}' is already registered. The new definition will override the existing one."
            )
        self._tools[tool.name] = RegisteredTool(instance=tool)

    def _discover_modules(self, package_name: str) -> List[str]:
        """
        递归发现包内所有候选模块。
        """
        package = importlib.import_module(package_name)
        package_path = getattr(package, "__path__", None)
        if package_path is None:
            return [package_name]

        modules = [package_name]
        for module_info in pkgutil.walk_packages(package_path, prefix=f"{package_name}."):
            module_basename = module_info.name.rsplit(".", 1)[-1]
            if module_basename.startswith("_"):
                continue
            modules.append(module_info.name)
        return modules

    def load_from_package(self, package_name: str) -> None:
        """
        从指定 Python 包中递归扫描并自动注册所有 BaseTool 子类。
        """
        for module_name in self._discover_modules(package_name):
            try:
                module = importlib.import_module(module_name)
            except Exception as exc:
                logger.error(f"Failed to import tool module '{module_name}': {exc}", exc_info=True)
                continue

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj is BaseTool or not issubclass(obj, BaseTool):
                    continue
                if inspect.isabstract(obj):
                    continue
                if obj.__module__ != module.__name__:
                    continue

                try:
                    self.register_tool(obj())
                except Exception as exc:
                    logger.error(
                        f"Failed to initialize tool class '{obj.__name__}' from module '{module_name}': {exc}",
                        exc_info=True,
                    )

    def list_definitions(self, scopes: Optional[Iterable[str]] = None) -> List[ToolDefinition]:
        """
        获取可用工具列表；若指定 scopes，则只返回匹配作用域的工具。
        """
        if scopes is None:
            return [tool.definition for tool in self._tools.values()]

        scope_set = set(scopes)
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
        执行指定工具，并统一返回字典格式结果。
        """
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"未找到名为 '{name}' 的已注册工具。")

        result = await tool.instance.execute(context=context, **parameters)
        if isinstance(result, dict):
            return result
        return {"result": result}
