import shutil
from pathlib import Path

from typing import Dict, Optional, Type, TypeVar, Tuple

import toml
from pydantic import BaseModel, ValidationError

from .schemas.bot_config import BotConfig
from .schemas.llm_api_config import LLMApiConfig

T = TypeVar("T", bound=BaseModel)


class ConfigService:
    """
    通用配置加载服务，负责：
    - 按名称加载并校验配置
    - 缓存已加载的配置
    - 在缺失 llm_api 配置时自动生成模板
    """

    _instance = None
    _cache: Dict[str, BaseModel] = {}
    _config_registry: Dict[str, Tuple[str, Type[BaseModel]]] = {
        "llm_api": ("configs/llm_api_config.toml", LLMApiConfig),
        "bot": ("configs/bot_config.toml", BotConfig),
    }
    _llm_template_path = Path("configs/llm_api_config.template.toml")
    _llm_placeholder_values = {
        "",
        "your-api-key",
        "your-api-key-here",
        "your-openai-api-key",
        "your-bailian-key",
        "your-google-api-key",
        "your-google-api-key-1",
        "sk-your-key-here",
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigService, cls).__new__(cls)
        return cls._instance

    def get_config(self, name: str) -> T:
        if name in self._cache:
            return self._cache[name]  # type: ignore[return-value]

        if name not in self._config_registry:
            raise RuntimeError(f"未注册的配置名称: '{name}'。")

        config_path_str, schema_class = self._config_registry[name]
        config_path = Path(config_path_str)

        if not config_path.exists():
            self._handle_missing_config(name=name, config_path=config_path)

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = toml.load(f)

            validated_config = schema_class.model_validate(data)

            if name == "llm_api":
                self._validate_llm_api_config(validated_config)

            self._cache[name] = validated_config
            return validated_config  # type: ignore[return-value]

        except ValidationError as e:
            raise RuntimeError(
                f"配置文件 '{config_path_str}' (用于 '{name}') 格式错误:\n{e}"
            ) from e
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"加载配置文件 '{config_path_str}' (用于 '{name}') 时发生未知错误: {e}"
            ) from e

    def clear_cache(self, name: Optional[str] = None):
        if name:
            self._cache.pop(name, None)
        else:
            self._cache.clear()

    def _handle_missing_config(self, name: str, config_path: Path) -> None:
        if name == "llm_api":
            self._create_llm_template_config(config_path)
            raise RuntimeError(
                f"未找到配置文件，已自动生成模板: {config_path.resolve()}。"
                "请先补全 api_key、模型和 provider 配置后再重新启动。"
            )

        raise RuntimeError(f"配置文件未找到: {config_path.resolve()}")

    def _create_llm_template_config(self, config_path: Path) -> None:
        config_path.parent.mkdir(parents=True, exist_ok=True)

        if not self._llm_template_path.exists():
            raise RuntimeError(
                f"缺少 LLM 配置模板文件: {self._llm_template_path.resolve()}，"
                "无法自动生成 llm_api_config.toml。"
            )

        shutil.copyfile(self._llm_template_path, config_path)

    def _validate_llm_api_config(self, config: LLMApiConfig) -> None:
        used_model_names = {
            model_name
            for task_config in config.model_task_config.values()
            for model_name in task_config.model_list
        }
        used_provider_names = {
            model.api_provider
            for model in config.models
            if model.name in used_model_names
        }
        invalid_providers = [
            provider.name
            for provider in config.api_providers
            if provider.name in used_provider_names
            and provider.api_key.strip() in self._llm_placeholder_values
        ]

        if invalid_providers:
            raise RuntimeError(
                "检测到 llm_api_config.toml 中仍存在未填写的占位 api_key，请完善以下 provider 后重试: "
                + ", ".join(invalid_providers)
            )
