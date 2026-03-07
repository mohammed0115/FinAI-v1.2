from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('auditor', 'Auditor'),
        ('accountant', 'Accountant'),
        ('finance_manager', 'Finance Manager'),
        ('admin', 'Admin'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    organization = models.ForeignKey('Organization', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    login_method = models.CharField(max_length=64, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_signed_in = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['organization']),
        ]
    
    def __str__(self):
        return self.email

class Organization(models.Model):
    """
    منظمة / شركة - Organization / Company
    
    VAT HANDLING LOGIC:
    - Saudi Arabia (SA): VAT number REQUIRED, must be valid ZATCA format
    - Other GCC countries: VAT number OPTIONAL
    - VAT settings drive compliance checks and ZATCA verification scope
    - Does NOT affect audit scoring or create/modify transactions
    """
    COUNTRY_CHOICES = [
        ('SA', 'Saudi Arabia - المملكة العربية السعودية'),
        ('AE', 'United Arab Emirates - الإمارات العربية المتحدة'),
        ('BH', 'Bahrain - البحرين'),
        ('KW', 'Kuwait - الكويت'),
        ('OM', 'Oman - عمان'),
        ('QA', 'Qatar - قطر'),
    ]
    
    COMPANY_TYPE_CHOICES = [
        ('government', 'Government - حكومي'),
        ('semi_government', 'Semi-Government - شبه حكومي'),
        ('private', 'Private - خاص'),
        ('sme', 'SME - منشأة صغيرة ومتوسطة'),
    ]
    
    VAT_VALIDATION_STATUS_CHOICES = [
        ('not_validated', 'لم يتم التحقق - Not Validated'),
        ('valid', 'صالح - Valid'),
        ('invalid', 'غير صالح - Invalid'),
        ('not_required', 'غير مطلوب - Not Required'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text='اسم الشركة')
    name_ar = models.CharField(max_length=255, null=True, blank=True, help_text='اسم الشركة بالعربية')
    logo = models.ImageField(upload_to='org_logos/', null=True, blank=True, help_text='شعار الشركة')
    country = models.CharField(max_length=2, choices=COUNTRY_CHOICES, help_text='البلد')
    
    # VAT Fields
    vat_number = models.CharField(
        max_length=20, 
        null=True, 
        blank=True,
        help_text='رقم التسجيل في ضريبة القيمة المضافة'
    )
    vat_applicable = models.BooleanField(
        default=False,
        help_text='هل تنطبق ضريبة القيمة المضافة على هذه الشركة؟'
    )
    vat_validation_status = models.CharField(
        max_length=20,
        choices=VAT_VALIDATION_STATUS_CHOICES,
        default='not_validated',
        help_text='حالة التحقق من رقم ضريبة القيمة المضافة'
    )
    vat_validation_message = models.TextField(
        null=True, 
        blank=True,
        help_text='رسالة التحقق من رقم ضريبة القيمة المضافة'
    )
    vat_validated_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text='تاريخ التحقق من رقم ضريبة القيمة المضافة'
    )
    
    # ZATCA Settings
    zatca_enabled = models.BooleanField(
        default=False,
        help_text='تفعيل التحقق من هيئة الزكاة والضريبة والجمارك'
    )
    zatca_verification_scope = models.CharField(
        max_length=50,
        default='disabled',
        choices=[
            ('disabled', 'معطل - Disabled'),
            ('verification_only', 'التحقق فقط - Verification Only'),
        ],
        help_text='نطاق التحقق من ZATCA'
    )
    
    # Legacy fields (kept for compatibility)
    tax_id = models.CharField(max_length=100, null=True, blank=True)
    vat_rate = models.IntegerField(default=15)  # VAT rate in percentage
    currency = models.CharField(max_length=10, default='SAR')
    industry = models.CharField(max_length=100, null=True, blank=True)
    company_type = models.CharField(max_length=20, choices=COMPANY_TYPE_CHOICES, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'organizations'
    
    def __str__(self):
        return self.name
    
    @property
    def is_saudi(self) -> bool:
        """Check if organization is in Saudi Arabia"""
        return self.country == 'SA'
    
    @property
    def requires_vat(self) -> bool:
        """Check if VAT number is required based on country"""
        return self.country == 'SA'
    
    def get_vat_status_display_ar(self) -> str:
        """Get Arabic display for VAT validation status"""
        status_ar = {
            'not_validated': 'لم يتم التحقق',
            'valid': 'صالح',
            'invalid': 'غير صالح',
            'not_required': 'غير مطلوب',
        }
        return status_ar.get(self.vat_validation_status, self.vat_validation_status)

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50)
    entity_id = models.UUIDField(null=True, blank=True)
    old_value_json = models.JSONField(null=True, blank=True)
    new_value_json = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['user']),
            models.Index(fields=['action']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.action}"

class Configuration(models.Model):
    CONFIG_TYPE_CHOICES = [
        ('system', 'System'),
        ('organization', 'Organization'),
        ('user', 'User'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True, related_name='configurations')
    config_key = models.CharField(max_length=100)
    config_value = models.TextField()
    config_type = models.CharField(max_length=20, choices=CONFIG_TYPE_CHOICES, default='system')
    description = models.TextField(null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'configurations'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['config_key']),
        ]
        unique_together = [['organization', 'config_key']]
    
    def __str__(self):
        return f"{self.config_key}: {self.config_value}"
