from rest_framework import generics, status, permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from .models import AcademicProgram, StudentApplication
from .serializers import (
    AcademicProgramSerializer, 
    StudentApplicationSerializer,
    ApplicationSubmissionSerializer
)


class AcademicProgramListView(generics.ListAPIView):
    """List all active academic programs"""
    queryset = AcademicProgram.objects.filter(is_active=True)
    serializer_class = AcademicProgramSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['level', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'application_deadline', 'created_at']
    ordering = ['level']


class AcademicProgramDetailView(generics.RetrieveAPIView):
    """Get details of a specific academic program"""
    queryset = AcademicProgram.objects.filter(is_active=True)
    serializer_class = AcademicProgramSerializer
    permission_classes = [permissions.AllowAny]


class StudentApplicationListCreateView(generics.ListCreateAPIView):
    """List user's applications or create new application"""
    serializer_class = StudentApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'program__level']
    search_fields = ['first_name', 'last_name', 'application_id']
    ordering_fields = ['created_at', 'submitted_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return StudentApplication.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        # Check if user already has an application for this program
        program = serializer.validated_data['program']
        existing_app = StudentApplication.objects.filter(
            user=self.request.user, 
            program=program
        ).first()
        
        if existing_app:
            raise serializers.ValidationError(
                "You already have an application for this program."
            )
        
        serializer.save(user=self.request.user)


class StudentApplicationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete a specific application"""
    serializer_class = StudentApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return StudentApplication.objects.filter(user=self.request.user)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != 'draft':
            return Response(
                {'error': 'Only draft applications can be modified.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != 'draft':
            return Response(
                {'error': 'Only draft applications can be deleted.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def submit_application(request, pk):
    """Submit an application for review"""
    application = get_object_or_404(
        StudentApplication, 
        pk=pk, 
        user=request.user
    )
    
    serializer = ApplicationSubmissionSerializer(
        application, 
        data={}, 
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Application submitted successfully',
            'application_id': application.application_id,
            'status': application.status
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def application_statistics(request):
    """Get application statistics for the current user"""
    user_applications = StudentApplication.objects.filter(user=request.user)
    
    stats = {
        'total_applications': user_applications.count(),
        'draft_applications': user_applications.filter(status='draft').count(),
        'submitted_applications': user_applications.filter(status='submitted').count(),
        'approved_applications': user_applications.filter(status='approved').count(),
        'rejected_applications': user_applications.filter(status='rejected').count(),
        'under_review': user_applications.filter(status='under_review').count(),
        'waitlisted': user_applications.filter(status='waitlisted').count(),
    }
    
    return Response(stats)


# Admin views (for staff/admin users)
class AdminApplicationListView(generics.ListAPIView):
    """Admin view to list all applications with filtering"""
    queryset = StudentApplication.objects.all()
    serializer_class = StudentApplicationSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'program__level', 'application_fee_paid']
    search_fields = ['first_name', 'last_name', 'application_id', 'email']
    ordering_fields = ['created_at', 'submitted_at', 'status']
    ordering = ['-created_at']


@api_view(['PATCH'])
@permission_classes([permissions.IsAdminUser])
def update_application_status(request, pk):
    """Admin endpoint to update application status"""
    application = get_object_or_404(StudentApplication, pk=pk)
    
    new_status = request.data.get('status')
    reviewer_comments = request.data.get('reviewer_comments', '')
    
    if new_status not in dict(StudentApplication.STATUS_CHOICES):
        return Response(
            {'error': 'Invalid status'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    application.status = new_status
    application.reviewer_comments = reviewer_comments
    application.reviewed_at = timezone.now()
    application.save()
    
    return Response({
        'message': 'Application status updated successfully',
        'application_id': application.application_id,
        'status': application.status
    })