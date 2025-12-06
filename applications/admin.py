from django.contrib import admin
from django.utils.html import format_html
from .models import AcademicProgram, StudentApplication


@admin.register(AcademicProgram)
class AcademicProgramAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'duration_years', 'application_fee', 'application_deadline', 'is_active']
    list_filter = ['level', 'is_active', 'application_deadline']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    ordering = ['level', 'name']


@admin.register(StudentApplication)
class StudentApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'application_id', 'full_name', 'program', 'status', 
        'application_fee_paid', 'submitted_at', 'created_at'
    ]
    list_filter = [
        'status', 'program__level', 'application_fee_paid', 
        'gender', 'nationality', 'created_at'
    ]
    search_fields = [
        'application_id', 'first_name', 'last_name', 'email', 
        'user__username', 'user__email'
    ]
    list_editable = ['status']
    readonly_fields = ['application_id', 'created_at', 'updated_at', 'submitted_at']
    
    fieldsets = (
        ('Application Info', {
            'fields': ('application_id', 'user', 'program', 'status', 'application_fee_paid')
        }),
        ('Personal Information', {
            'fields': (
                'first_name', 'middle_name', 'last_name', 'date_of_birth',
                'gender', 'nationality', 'marital_status'
            )
        }),
        ('Contact Information', {
            'fields': (
                'email', 'phone_number', 'address_line_1', 'address_line_2',
                'city', 'state_province', 'postal_code', 'country'
            )
        }),
        ('Emergency Contact', {
            'fields': (
                'emergency_contact_name', 'emergency_contact_phone',
                'emergency_contact_relationship'
            )
        }),
        ('Academic & Ministry Background', {
            'fields': (
                'previous_education', 'current_church_affiliation', 
                'pastoral_experience'
            )
        }),
        ('Documents', {
            'fields': (
                'transcript', 'personal_statement', 'recommendation_letter_1',
                'recommendation_letter_2', 'passport_photo'
            )
        }),
        ('Review Information', {
            'fields': ('reviewer_comments', 'reviewed_at', 'submitted_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'program')
