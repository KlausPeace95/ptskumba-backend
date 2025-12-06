from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator, FileExtensionValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta


def validate_age(birth_date):
    """Validate that applicant is at least 25 years old"""
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    if age < 25:
        raise ValidationError('Applicant must be at least 25 years old.')


def validate_file_size(file):
    """Validate file size is less than 5MB"""
    filesize = file.size
    if filesize > 5242880:  # 5MB in bytes
        raise ValidationError("Maximum file size is 5MB")


class ExamVenue(models.Model):
    """Model for examination venues/locations"""
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    capacity = models.IntegerField(default=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['city', 'name']
        verbose_name = 'Exam Venue'
        verbose_name_plural = 'Exam Venues'

    def __str__(self):
        return f"{self.name} - {self.city}"


class ExamSession(models.Model):
    """Model for examination sessions with dates and venues"""
    venue = models.ForeignKey(ExamVenue, on_delete=models.PROTECT, related_name='sessions')
    exam_date = models.DateField()
    exam_time = models.TimeField()
    registration_deadline = models.DateField()
    max_applicants = models.IntegerField(default=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-exam_date']
        verbose_name = 'Exam Session'
        verbose_name_plural = 'Exam Sessions'

    def __str__(self):
        return f"{self.venue.name} - {self.exam_date}"

    def clean(self):
        if self.exam_date and self.exam_date < date.today():
            raise ValidationError({'exam_date': 'Exam date cannot be in the past.'})
        if self.registration_deadline and self.registration_deadline >= self.exam_date:
            raise ValidationError({'registration_deadline': 'Registration deadline must be before exam date.'})


class Application(models.Model):
    """Model for B.Th. entrance examination applications"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]

    MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('widowed', 'Widowed'),
        ('divorced', 'Divorced'),
    ]

    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(validators=[validate_age])
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES)
    nationality = models.CharField(max_length=100, default='Cameroonian')
    
    # Contact Information
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    
    # Church Information
    congregation_name = models.CharField(max_length=200)
    years_in_congregation = models.IntegerField()
    
    # Pastor Contact
    pastor_name = models.CharField(max_length=200)
    pastor_phone = models.CharField(max_length=20)
    pastor_email = models.EmailField()
    
    # Chairperson Contact
    chairperson_name = models.CharField(max_length=200)
    chairperson_phone = models.CharField(max_length=20)
    chairperson_email = models.EmailField()
    
    # Educational Background
    last_school_attended = models.CharField(max_length=200)
    graduation_year = models.IntegerField()
    
    # Document Uploads
    birth_certificate = models.FileField(
        upload_to='applications/birth_certificates/',
        validators=[validate_file_size, FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )
    transcripts = models.FileField(
        upload_to='applications/transcripts/',
        validators=[validate_file_size, FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )
    gce_a_level = models.FileField(
        upload_to='applications/gce_a_level/',
        validators=[validate_file_size, FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )
    gce_o_level = models.FileField(
        upload_to='applications/gce_o_level/',
        validators=[validate_file_size, FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )
    passport_photo = models.ImageField(
        upload_to='applications/photos/',
        validators=[validate_file_size, FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    
    # Motivation
    motivation = models.TextField(
        validators=[MaxLengthValidator(2000)],
        help_text='Maximum 2000 characters'
    )
    
    # Exam Venue Selection
    preferred_venue = models.ForeignKey(
        ExamVenue,
        on_delete=models.PROTECT,
        related_name='applications'
    )
    
    # Application Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    assigned_session = models.ForeignKey(
        ExamSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications'
    )
    
    # Admin Notes
    admin_notes = models.TextField(blank=True)
    reviewed_by = models.CharField(max_length=200, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Application'
        verbose_name_plural = 'Applications'
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.get_status_display()}"

    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

    def clean(self):
        # Validate age
        validate_age(self.date_of_birth)
        
        # Validate motivation length
        if len(self.motivation) > 2000:
            raise ValidationError({'motivation': 'Motivation paragraph must not exceed 2000 characters.'})


class EmailLog(models.Model):
    """Model to track emails sent to applicants"""
    
    EMAIL_TYPE_CHOICES = [
        ('acceptance', 'Acceptance Email'),
        ('rejection', 'Rejection Email'),
        ('confirmation', 'Application Confirmation'),
    ]

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='email_logs'
    )
    email_type = models.CharField(max_length=20, choices=EMAIL_TYPE_CHOICES)
    sent_to = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    was_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'

    def __str__(self):
        return f"{self.get_email_type_display()} to {self.sent_to} - {self.sent_at}"