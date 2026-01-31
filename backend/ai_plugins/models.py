
from django.db import models
from .ai_plugins import AI_LIBRARIES

AI_PROVIDER_CHOICES = [
    (lib["provider"], lib["name"]) for lib in AI_LIBRARIES
]

class AIPluginSetting(models.Model):
    plugin_code = models.CharField(max_length=100, unique=True)

    provider = models.CharField(
        max_length=50,
        choices=AI_PROVIDER_CHOICES,
        default="Gensim"  # OpenAI is default if free, otherwise set to 'local'
    )

    model_name = models.CharField(max_length=100, blank=True)
    temperature = models.FloatField(default=0.0)
    max_tokens = models.IntegerField(default=2048)

    prompt_text = models.TextField(blank=True)

    is_enabled = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.plugin_code
