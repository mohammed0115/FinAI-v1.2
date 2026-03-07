from django.db import models

class AI(models.Model):
    """
    نموذج مخصص لإعدادات الذكاء الاصطناعي (customized AI)
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="التسمية الإدارية")
    provider = models.CharField(max_length=50, verbose_name="التقنية")
    model_name = models.CharField(max_length=100, blank=True, verbose_name="اسم النموذج")
    python_module = models.CharField(max_length=100, blank=True, verbose_name="مكتبة بايثون")
    tesseract_path = models.CharField(max_length=255, blank=True, verbose_name="مسار Tesseract (لـ OCR)")
    label = models.CharField(max_length=100, blank=True, verbose_name="الوظيفة")
    is_enabled = models.BooleanField(default=True, verbose_name="مفعل")
    config_json = models.JSONField(blank=True, null=True, verbose_name="إعدادات إضافية")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
