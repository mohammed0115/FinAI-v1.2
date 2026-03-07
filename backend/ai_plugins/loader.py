import importlib
from pathlib import Path

PLUGINS_DIR = Path(__file__).parent / "plugins"
# backend/ai_plugins/loader.py
import importlib
import inspect
from pathlib import Path
from ai_plugins.base import AIPlugin

PLUGINS_DIR = Path(__file__).parent / "plugins"


class AIPluginLoader:
    _plugins = {}

    @classmethod
    def load(cls):
        cls._plugins = {}

        for p in PLUGINS_DIR.iterdir():
            if not p.is_dir():
                continue

            module_path = f"ai_plugins.plugins.{p.name}.plugin"
            module = importlib.import_module(module_path)

            for _, obj in module.__dict__.items():
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, AIPlugin)
                    and obj is not AIPlugin
                ):
                    instance = obj()
                    cls._plugins[instance.code] = instance

    @classmethod
    def get(cls, code: str):
        return cls._plugins.get(code)
