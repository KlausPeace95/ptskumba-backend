from rest_framework import serializers
from .models import Application, ExamVenue, ExamSession, EmailLog
from datetime import date


class ExamVenueSerializer(serializers.ModelSerializer):
    """Serializer for exam venues"""
    
    class Meta:
        model = ExamVenue
        fields = ['id', 'name', 'address', 'city', 'capacity', 'is_active']
        read_only_fields = ['id']


class ExamSessionSerializer(serializers.ModelSerializer):
    """Serializer for exam sessions"""
    venue_details = ExamVenueSerializer(source='venue', read_only=True)
    applicants_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ExamSession
        fields = [
            'id', 'venue', 'venue_details', 'exam_date', 'exam_time',
            'registration_deadline', 'max_applicants', 'applicants_count',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_applicants_count(self, obj):
        return obj.applications.filter(status='accepted').count()

    def validate(self, data):
        if data.get('exam_date') and data['exam_date'] < date.today():
            raise serializers.ValidationError({
                'exam_date': 'Exam date cannot be in the past.'
            })
        
        if data.get('registration_deadline') and data.get('exam_date'):
            if data['registration_deadline'] >= data['exam_date']:
                raise serializers.ValidationError({
                    'registration_deadline': 'Registration deadline must be before exam date.'
                })
        
        return data


class ApplicationListSerializer(serializers.ModelSerializer):
    """Serializer for listing applications (limited fields)"""
    venue_name = serializers.CharField(source='preferred_venue.name', read_only=True)
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Application
        fields = [
            'id', 'full_name', 'email', 'phone_number', 'age',
            'congregation_name', 'venue_name', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields


class ApplicationDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed application view"""
    venue_details = ExamVenueSerializer(source='preferred_venue', read_only=True)
    session_details = ExamSessionSerializer(source='assigned_session', read_only=True)
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Application
        fields = [
            'id', 'first_name', 'last_name', 'middle_name', 'full_name',
            'date_of_birth', 'age', 'gender', 'marital_status', 'nationality',
            'email', 'phone_number', 'address', 'city', 'region',
            'congregation_name', 'years_in_congregation',
            'pastor_name', 'pastor_phone', 'pastor_email',
            'chairperson_name', 'chairperson_phone', 'chairperson_email',
            'last_school_attended', 'graduation_year',
            'birth_certificate', 'transcripts', 'gce_a_level', 'gce_o_level',
            'passport_photo', 'motivation', 'preferred_venue', 'venue_details',
            'status', 'assigned_session', 'session_details',
            'admin_notes', 'reviewed_by', 'reviewed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'full_name', 'age', 'status', 'assigned_session',
            'admin_notes', 'reviewed_by', 'reviewed_at',
            'created_at', 'updated_at'
        ]


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new applications"""
    
    class Meta:
        model = Application
        fields = [
            'first_name', 'last_name', 'middle_name', 'date_of_birth',
            'gender', 'marital_status', 'nationality',
            'email', 'phone_number', 'address', 'city', 'region',
            'congregation_name', 'years_in_congregation',
            'pastor_name', 'pastor_phone', 'pastor_email',
            'chairperson_name', 'chairperson_phone', 'chairperson_email',
            'last_school_attended', 'graduation_year',
            'birth_certificate', 'transcripts', 'gce_a_level', 'gce_o_level',
            'passport_photo', 'motivation', 'preferred_venue'
        ]

    def validate_date_of_birth(self, value):
        """Validate that applicant is at least 25 years old"""
        today = date.today()
        age = today.year - value.year - ((today.month, value.day) < (value.month, value.day))
        if age < 25:
            raise serializers.ValidationError('You must be at least 25 years old to apply.')
        return value

    def validate_motivation(self, value):
        """Validate motivation paragraph length"""
        if len(value) > 2000:
            raise serializers.ValidationError('Motivation paragraph must not exceed 2000 characters.')
        return value

    def validate_preferred_venue(self, value):
        """Validate that the venue is active"""
        if not value.is_active:
            raise serializers.ValidationError('This venue is no longer accepting applications.')
        return value

    def validate_years_in_congregation(self, value):
        """Validate years in congregation"""
        if value < 0:
            raise serializers.ValidationError('Years in congregation cannot be negative.')
        return value

    def validate_graduation_year(self, value):
        """Validate graduation year"""
        current_year = date.today().year
        if value < 1950 or value > current_year:
            raise serializers.ValidationError(f'Graduation year must be between 1950 and {current_year}.')
        return value


class ApplicationStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admin to update application status"""
    
    class Meta:
        model = Application
        fields = ['status', 'assigned_session', 'admin_notes', 'reviewed_by']

    def validate(self, data):
        """Validate status update"""
        if data.get('status') == 'accepted' and not data.get('assigned_session'):
            raise serializers.ValidationError({
                'assigned_session': 'Accepted applications must have an assigned exam session.'
            })
        return data


class BulkStatusUpdateSerializer(serializers.Serializer):
    """Serializer for bulk status updates"""
    application_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )
    status = serializers.ChoiceField(choices=['accepted', 'rejected'])
    assigned_session = serializers.PrimaryKeyRelatedField(
        queryset=ExamSession.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )
    admin_notes = serializers.CharField(required=False, allow_blank=True)
    reviewed_by = serializers.CharField(max_length=200)

    def validate(self, data):
        """Validate bulk update"""
        if data['status'] == 'accepted' and not data.get('assigned_session'):
            raise serializers.ValidationError({
                'assigned_session': 'Accepted applications must have an assigned exam session.'
            })
        return data


class EmailLogSerializer(serializers.ModelSerializer):
    """Serializer for email logs"""
    application_name = serializers.CharField(source='application.full_name', read_only=True)
    
    class Meta:
        model = EmailLog
        fields = [
            'id', 'application', 'application_name', 'email_type',
            'sent_to', 'subject', 'body', 'sent_at',
            'was_successful', 'error_message'
        ]
        read_only_fields = fields