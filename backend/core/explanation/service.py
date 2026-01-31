from .static_explanation import StaticExplanationProvider

class ExplanationService:
    def __init__(self):
        self.provider = StaticExplanationProvider()

    def generate(self, context):
        return self.provider.explain(context)
