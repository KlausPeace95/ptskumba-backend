from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Application, ExamVenue, ExamSession, EmailLog


@admin.register(ExamVenue)
class ExamVenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'capacity', 'is_active', 'created_at']
    list_filter = ['is_active', 'city', 'created_at']
    search_fields = ['name', 'city', 'address']
    ordering = ['city', 'name']
    list_editable = ['is_active']
    
    fieldsets = (
        ('Venue Information', {
            'fields': ('name', 'address', 'city', 'capacity')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = [
        'venue', 'exam_date', 'exam_time', 'registration_deadline',
        'applicants_count', 'max_applicants', 'is_active'
    ]
    list_filter = ['is_active', 'exam_date', 'venue__city']
    search_fields = ['venue__name', 'venue__city']
    ordering = ['-exam_date']
    list_editable = ['is_active']
    date_hierarchy = 'exam_date'
    
    fieldsets = (
        ('Session Details', {
            'fields': ('venue', 'exam_date', 'exam_time', 'registration_deadline')
        }),
        ('Capacity', {
            'fields': ('max_applicants',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def applicants_count(self, obj):
        count = obj.applications.filter(status='accepted').count()
        return f"{count}/{obj.max_applicants}"
    applicants_count.short_description = 'Applicants'


class EmailLogInline(admin.TabularInline):
    model = EmailLog
    extra = 0
    readonly_fields = ['email_type', 'sent_to', 'subject', 'sent_at', 'was_successful']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'full_name', 'email', 'age', 'congregation_name',
        'preferred_venue', 'status_badge', 'created_at'
    ]
    list_filter = [
        'status', 'gender', 'marital_status',
        'preferred_venue__city', 'created_at'
    ]
    search_fields = [
        'first_name', 'last_name', 'email', 'phone_number',
        'congregation_name', 'pastor_name', 'chairperson_name'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    readonly_fields = [
        'full_name', 'age', 'created_at', 'updated_at',
        'birth_certificate_preview', 'passport_photo_preview'
    ]
    
    inlines = [EmailLogInline]
    
    fieldsets = (
        ('Personal Information', {
            'fields': (
                'first_name', 'last_name', 'middle_name', 'full_name',
                'date_of_birth', 'age', 'gender', 'marital_status', 'nationality'
            )
        }),
        ('Contact Information', {
            'fields': ('email', 'phone_number', 'address', 'city', 'region')
        }),
        ('Church Information', {
            'fields': ('congregation_name', 'years_in_congregation')
        }),
        ('Pastor Reference', {
            'fields': ('pastor_name', 'pastor_phone', 'pastor_email')
        }),
        ('Chairperson Reference', {
            'fields': ('chairperson_name', 'chairperson_phone', 'chairperson_email')
        }),
        ('Educational Background', {
            'fields': ('last_school_attended', 'graduation_year')
        }),
        ('Documents', {
            'fields': (
                'birth_certificate', 'birth_certificate_preview',
                'transcripts', 'gce_a_level', 'gce_o_level',
                'passport_photo', 'passport_photo_preview'
            )
        }),
        ('Motivation', {
            'fields': ('motivation',)
        }),
        ('Exam Details', {
            'fields': ('preferred_venue', 'assigned_session')
        }),
        ('Application Status', {
            'fields': ('status', 'admin_notes', 'reviewed_by', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['accept_applications', 'reject_applications', 'export_to_csv']
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffa500',
            'accepted': '#28a745',
            'rejected': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def birth_certificate_preview(self, obj):
        if obj.birth_certificate:
            if obj.birth_certificate.name.endswith(('.jpg', '.jpeg', '.png')):
                return format_html(
                    '<a href="{}" target="_blank"><img src="{}" style="max-width: 200px; max-height: 200px;"/></a>',
                    obj.birth_certificate.url,
                    obj.birth_certificate.url
                )
            return format_html(
                '<a href="{}" target="_blank">View Document</a>',
                obj.birth_certificate.url
            )
        return "No file uploaded"
    birth_certificate_preview.short_description = 'Birth Certificate Preview'
    
    def passport_photo_preview(self, obj):
        if obj.passport_photo:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 150px; max-height: 150px;"/></a>',
                obj.passport_photo.url,
                obj.passport_photo.url
            )
        return "No photo uploaded"
    passport_photo_preview.short_description = 'Passport Photo Preview'
    
    def accept_applications(self, request, queryset):
        # This is a placeholder - you'll need to implement session assignment logic
        updated = queryset.update(status='accepted', reviewed_by=request.user.username)
        self.message_user(request, f'{updated} application(s) marked as accepted.')
    accept_applications.short_description = 'Accept selected applications'
    
    def reject_applications(self, request, queryset):
        updated = queryset.update(status='rejected', reviewed_by=request.user.username)
        self.message_user(request, f'{updated} application(s) marked as rejected.')
    reject_applications.short_description = 'Reject selected applications'
    
    def export_to_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="applications.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Full Name', 'Email', 'Phone', 'Age', 'Gender',
            'Congregation', 'Preferred Venue', 'Status', 'Applied Date'
        ])
        
        for app in queryset:
            writer.writerow([
                app.id, app.full_name, app.email, app.phone_number,
                app.age, app.get_gender_display(), app.congregation_name,
                app.preferred_venue.name, app.get_status_display(),
                app.created_at.strftime('%Y-%m-%d')
            ])
        
        return response
    export_to_csv.short_description = 'Export selected to CSV'


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'application_link', 'email_type', 'sent_to',
        'sent_at', 'success_badge'
    ]
    list_filter = ['email_type', 'was_successful', 'sent_at']
    search_fields = ['sent_to', 'subject', 'application__first_name', 'application__last_name']
    ordering = ['-sent_at']
    date_hierarchy = 'sent_at'
    readonly_fields = [
        'application', 'email_type', 'sent_to', 'subject',
        'body', 'sent_at', 'was_successful', 'error_message'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def application_link(self, obj):
        url = reverse('admin:entrance_application_change', args=[obj.application.id])
        return format_html('<a href="{}">{}</a>', url, obj.application.full_name)
    application_link.short_description = 'Application'
    
    def success_badge(self, obj):
        if obj.was_successful:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; '
                'border-radius: 3px;">Success</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 10px; '
            'border-radius: 3px;">Failed</span>'
        )
    success_badge.short_description = 'Status'