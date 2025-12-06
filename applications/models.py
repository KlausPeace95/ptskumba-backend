from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator, RegexValidator
from django.utils import timezone
from datetime import date

User = get_user_model()

class AcademicProgram(models.Model):
    PROGRAM_LEVELS = [
        ('bachelor', 'Bachelor of Theology'),
        ('master', 'Master of Theology'),
        ('doctor', 'Doctor of Theology'),
    ]
    
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=PROGRAM_LEVELS, unique=True)
    description = models.TextField()
    duration_years = models.PositiveIntegerField()
    application_fee = models.DecimalField(max_digits=10, decimal_places=2)
    requirements = models.TextField(help_text="List program requirements")
    is_active = models.BooleanField(default=True)
    application_deadline = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['level', 'name']
    
    def __str__(self):
        return f"{self.get_level_display()}"
    
    @property
    def is_application_open(self):
        return self.is_active and self.application_deadline >= date.today()


class StudentApplication(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('waitlisted', 'Waitlisted'),
    ]
    
    MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ]
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    
    # Application Reference
    application_id = models.CharField(max_length=20, unique=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    program = models.ForeignKey(AcademicProgram, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Personal Information
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    nationality = models.CharField(max_length=50)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES)
    
    # Contact Information
    email = models.EmailField()
    phone_number = models.CharField(
        max_length=15, 
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number')]
    )
    address_line_1 = models.CharField(max_length=200)
    address_line_2 = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number')]
    )
    emergency_contact_relationship = models.CharField(max_length=50)
    
    # Academic Background
    previous_education = models.TextField(help_text="Describe your educational background")
    current_church_affiliation = models.CharField(max_length=200, blank=True, null=True)
    pastoral_experience = models.TextField(blank=True, null=True)
    
    # Application Documents
    transcript = models.FileField(
        upload_to='applications/transcripts/',
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx'])],
        help_text="Upload official academic transcripts"
    )
    personal_statement = models.FileField(
        upload_to='applications/statements/',
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx'])],
        help_text="Upload your personal statement/essay"
    )
    recommendation_letter_1 = models.FileField(
        upload_to='applications/recommendations/',
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx'])],
        help_text="First recommendation letter"
    )
    recommendation_letter_2 = models.FileField(
        upload_to='applications/recommendations/',
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx'])],
        blank=True, null=True,
        help_text="Second recommendation letter (optional)"
    )
    passport_photo = models.ImageField(
        upload_to='applications/photos/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        help_text="Upload passport-size photograph"
    )
    
    # Application Meta
    application_fee_paid = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(blank=True, null=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewer_comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'program']  # One application per user per program
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.program.name}"
    
    def save(self, *args, **kwargs):
        if not self.application_id:
            # Generate unique application ID
            year = timezone.now().year
            count = StudentApplication.objects.filter(
                created_at__year=year
            ).count() + 1
            self.application_id = f"APP-{year}-{count:04d}"
        super().save(*args, **kwargs)
    
    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    @property
    def can_submit(self):
        """Check if application has all required fields and documents"""
        required_fields = [
            self.first_name, self.last_name, self.date_of_birth,
            self.email, self.phone_number, self.address_line_1,
            self.city, self.country, self.transcript, self.personal_statement,
            self.recommendation_letter_1, self.passport_photo
        ]
        return all(field for field in required_fields) and self.status == 'draft'
