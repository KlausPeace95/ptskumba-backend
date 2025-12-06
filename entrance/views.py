from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone
from django.db.models import Q
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Application, ExamVenue, ExamSession, EmailLog
from .serializers import (
    ApplicationListSerializer, ApplicationDetailSerializer,
    ApplicationCreateSerializer, ApplicationStatusUpdateSerializer,
    BulkStatusUpdateSerializer, ExamVenueSerializer,
    ExamSessionSerializer, EmailLogSerializer
)
from .permissions import IsAdminOrReadOnly, IsOwnerOrAdmin


class ExamVenueViewSet(viewsets.ModelViewSet):
    """ViewSet for managing exam venues"""
    queryset = ExamVenue.objects.all()
    serializer_class = ExamVenueSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        """Return active venues for non-admin users"""
        if self.request.user.is_staff:
            return ExamVenue.objects.all()
        return ExamVenue.objects.filter(is_active=True)


class ExamSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing exam sessions"""
    queryset = ExamSession.objects.all()
    serializer_class = ExamSessionSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        """Return active sessions for non-admin users"""
        if self.request.user.is_staff:
            return ExamSession.objects.all()
        return ExamSession.objects.filter(is_active=True)


class ApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing applications"""
    queryset = Application.objects.all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return ApplicationListSerializer
        elif self.action == 'create':
            return ApplicationCreateSerializer
        elif self.action in ['update_status', 'bulk_update_status']:
            return ApplicationStatusUpdateSerializer
        return ApplicationDetailSerializer

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        queryset = Application.objects.select_related(
            'preferred_venue', 'assigned_session', 'assigned_session__venue'
        )
        
        if self.request.user.is_staff:
            # Admin can see all applications
            status_filter = self.request.query_params.get('status', None)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            return queryset
        
        # Regular users can only see their own applications
        if self.request.user.is_authenticated:
            return queryset.filter(email=self.request.user.email)
        
        return queryset.none()

    def create(self, request, *args, **kwargs):
        """Create a new application"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        
        # Send confirmation email
        self._send_confirmation_email(application)
        
        # Return detailed response
        response_serializer = ApplicationDetailSerializer(application)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAdminUser])
    def update_status(self, request, pk=None):
        """Update application status and send notification email"""
        application = self.get_object()
        serializer = ApplicationStatusUpdateSerializer(
            application,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        
        old_status = application.status
        serializer.save(reviewed_at=timezone.now())
        
        # Send notification email if status changed
        if old_status != application.status:
            if application.status == 'accepted':
                self._send_acceptance_email(application)
            elif application.status == 'rejected':
                self._send_rejection_email(application)
        
        response_serializer = ApplicationDetailSerializer(application)
        return Response(response_serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def bulk_update_status(self, request):
        """Bulk update application statuses"""
        serializer = BulkStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        application_ids = data['application_ids']
        new_status = data['status']
        assigned_session = data.get('assigned_session')
        admin_notes = data.get('admin_notes', '')
        reviewed_by = data['reviewed_by']
        
        applications = Application.objects.filter(id__in=application_ids)
        
        updated_count = 0
        for application in applications:
            application.status = new_status
            application.assigned_session = assigned_session
            application.admin_notes = admin_notes
            application.reviewed_by = reviewed_by
            application.reviewed_at = timezone.now()
            application.save()
            
            # Send notification emails
            if new_status == 'accepted':
                self._send_acceptance_email(application)
            elif new_status == 'rejected':
                self._send_rejection_email(application)
            
            updated_count += 1
        
        return Response({
            'message': f'Successfully updated {updated_count} application(s)',
            'updated_count': updated_count
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get application statistics (admin only)"""
        if not request.user.is_staff:
            return Response(
                {'detail': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        total = Application.objects.count()
        pending = Application.objects.filter(status='pending').count()
        accepted = Application.objects.filter(status='accepted').count()
        rejected = Application.objects.filter(status='rejected').count()
        
        return Response({
            'total': total,
            'pending': pending,
            'accepted': accepted,
            'rejected': rejected
        })

    def _send_confirmation_email(self, application):
        """Send application confirmation email"""
        subject = 'Application Received - Presbyterian Theological Seminary'
        message = f"""
Dear {application.full_name},

Thank you for applying to the Presbyterian Theological Seminary of Kumba-Cameroon for the Bachelor of Theology (B.Th.) program.

Your application has been received and is currently under review. You will receive an email notification once a decision has been made regarding your application.

Application Details:
- Name: {application.full_name}
- Email: {application.email}
- Preferred Venue: {application.preferred_venue.name}, {application.preferred_venue.city}
- Submission Date: {application.created_at.strftime('%B %d, %Y')}

If you have any questions, please contact us at the seminary office.

God bless you,
Presbyterian Theological Seminary of Kumba
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [application.email],
                fail_silently=False,
            )
            
            EmailLog.objects.create(
                application=application,
                email_type='confirmation',
                sent_to=application.email,
                subject=subject,
                body=message,
                was_successful=True
            )
        except Exception as e:
            EmailLog.objects.create(
                application=application,
                email_type='confirmation',
                sent_to=application.email,
                subject=subject,
                body=message,
                was_successful=False,
                error_message=str(e)
            )

    def _send_acceptance_email(self, application):
        """Send acceptance email with exam details"""
        if not application.assigned_session:
            return
        
        session = application.assigned_session
        venue = session.venue
        
        subject = 'Application Accepted - Presbyterian Theological Seminary Entrance Examination'
        message = f"""
Dear {application.full_name},

Congratulations! We are pleased to inform you that your application to the Presbyterian Theological Seminary of Kumba-Cameroon for the Bachelor of Theology (B.Th.) program has been ACCEPTED.

You are invited to write the entrance examination as follows:

EXAMINATION DETAILS:
- Date: {session.exam_date.strftime('%A, %B %d, %Y')}
- Time: {session.exam_time.strftime('%I:%M %p')}
- Venue: {venue.name}
- Address: {venue.address}, {venue.city}

IMPORTANT INSTRUCTIONS:
1. Please arrive at least 30 minutes before the scheduled time
2. Bring a valid ID card and your printed application confirmation
3. Bring writing materials (pens, pencils)
4. Mobile phones are not allowed in the examination room

We look forward to seeing you on the examination day. May God grant you wisdom and understanding.

If you have any questions, please contact us at the seminary office.

God bless you,
Presbyterian Theological Seminary of Kumba
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [application.email],
                fail_silently=False,
            )
            
            EmailLog.objects.create(
                application=application,
                email_type='acceptance',
                sent_to=application.email,
                subject=subject,
                body=message,
                was_successful=True
            )
        except Exception as e:
            EmailLog.objects.create(
                application=application,
                email_type='acceptance',
                sent_to=application.email,
                subject=subject,
                body=message,
                was_successful=False,
                error_message=str(e)
            )

    def _send_rejection_email(self, application):
        """Send rejection email"""
        subject = 'Application Status - Presbyterian Theological Seminary'
        message = f"""
Dear {application.full_name},

Thank you for your interest in the Presbyterian Theological Seminary of Kumba-Cameroon and for taking the time to apply for the Bachelor of Theology (B.Th.) program.

After careful review of your application, we regret to inform you that we are unable to accept your application at this time.

We received many qualified applications and the selection process was very competitive. We encourage you to continue seeking God's guidance for your future ministry and calling.

We wish you all the best in your future endeavors and pray that God will lead you to the path He has prepared for you.

If you have any questions, please feel free to contact us at the seminary office.

God bless you,
Presbyterian Theological Seminary of Kumba
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [application.email],
                fail_silently=False,
            )
            
            EmailLog.objects.create(
                application=application,
                email_type='rejection',
                sent_to=application.email,
                subject=subject,
                body=message,
                was_successful=True
            )
        except Exception as e:
            EmailLog.objects.create(
                application=application,
                email_type='rejection',
                sent_to=application.email,
                subject=subject,
                body=message,
                was_successful=False,
                error_message=str(e)
            )


class EmailLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing email logs (admin only)"""
    queryset = EmailLog.objects.all()
    serializer_class = EmailLogSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        """Filter by application if provided"""
        queryset = EmailLog.objects.select_related('application')
        application_id = self.request.query_params.get('application', None)
        if application_id:
            queryset = queryset.filter(application_id=application_id)
        return queryset