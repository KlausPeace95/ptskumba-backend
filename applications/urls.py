from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    # Public program endpoints
    path('programs/', views.AcademicProgramListView.as_view(), name='program-list'),
    path('programs/<int:pk>/', views.AcademicProgramDetailView.as_view(), name='program-detail'),
    
    # Student application endpoints
    path('my-applications/', views.StudentApplicationListCreateView.as_view(), name='my-applications'),
    path('my-applications/<int:pk>/', views.StudentApplicationDetailView.as_view(), name='application-detail'),
    path('my-applications/<int:pk>/submit/', views.submit_application, name='submit-application'),
    path('statistics/', views.application_statistics, name='application-statistics'),
    
    # Admin endpoints
    path('admin/applications/', views.AdminApplicationListView.as_view(), name='admin-application-list'),
    path('admin/applications/<int:pk>/status/', views.update_application_status, name='update-application-status'),
]
