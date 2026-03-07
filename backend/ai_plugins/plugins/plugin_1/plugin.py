from ai_plugins.base import AIPlugin

class PluginOne(AIPlugin):
    code = "plugin_1"
    name = "Test Plugin 1"

    def execute(self, payload: dict) -> dict:
        return {
            "success": True,
            "message": "Plugin 1 executed successfully",
            "input": payload
        }



