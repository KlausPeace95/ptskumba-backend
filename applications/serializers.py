from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import AcademicProgram, StudentApplication

User = get_user_model()


class AcademicProgramSerializer(serializers.ModelSerializer):
    application_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AcademicProgram
        fields = [
            'id', 'name', 'level', 'description', 'duration_years',
            'application_fee', 'requirements', 'is_active',
            'application_deadline', 'is_application_open',
            'application_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_application_open', 'application_count']
    
    def get_application_count(self, obj):
        return obj.applications.count()


class StudentApplicationSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source='program.name', read_only=True)
    program_level = serializers.CharField(source='program.get_level_display', read_only=True)
    full_name = serializers.CharField(read_only=True)
    can_submit = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = StudentApplication
        fields = [
            'id', 'application_id', 'user', 'program', 'program_name', 
            'program_level', 'status', 'first_name', 'middle_name', 'last_name',
            'full_name', 'date_of_birth', 'gender', 'nationality', 'marital_status',
            'email', 'phone_number', 'address_line_1', 'address_line_2',
            'city', 'state_province', 'postal_code', 'country',
            'emergency_contact_name', 'emergency_contact_phone', 
            'emergency_contact_relationship', 'previous_education',
            'current_church_affiliation', 'pastoral_experience',
            'transcript', 'personal_statement', 'recommendation_letter_1',
            'recommendation_letter_2', 'passport_photo', 'application_fee_paid',
            'can_submit', 'submitted_at', 'reviewed_at', 'reviewer_comments',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'application_id', 'user', 'full_name', 'can_submit',
            'submitted_at', 'reviewed_at', 'created_at', 'updated_at'
        ]
    
    def validate(self, data):
        # Validate that application deadline hasn't passed
        if 'program' in data:
            program = data['program']
            if not program.is_application_open:
                raise serializers.ValidationError(
                    "Application deadline has passed for this program."
                )
        
        # Validate age for program eligibility
        if 'date_of_birth' in data:
            from datetime import date
            today = date.today()
            age = today.year - data['date_of_birth'].year - (
                (today.month, today.day) < (data['date_of_birth'].month, data['date_of_birth'].day)
            )
            if age < 18:
                raise serializers.ValidationError(
                    "Applicant must be at least 18 years old."
                )
        
        return data
    
    def create(self, validated_data):
        # Set user from request context
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ApplicationSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for submitting applications"""
    
    class Meta:
        model = StudentApplication
        fields = ['id', 'application_id', 'status']
        read_only_fields = ['id', 'application_id', 'status']
    
    def update(self, instance, validated_data):
        if not instance.can_submit:
            raise serializers.ValidationError(
                "Application cannot be submitted. Please complete all required fields and documents."
            )
        
        instance.status = 'submitted'
        instance.submitted_at = timezone.now()
        instance.save()
        return instance
