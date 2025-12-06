from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ApplicationViewSet,
    ExamVenueViewSet,
    ExamSessionViewSet,
    EmailLogViewSet
)

app_name = 'entrance'

router = DefaultRouter()
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'venues', ExamVenueViewSet, basename='venue')
router.register(r'sessions', ExamSessionViewSet, basename='session')
router.register(r'email-logs', EmailLogViewSet, basename='email-log')

urlpatterns = [
    path('', include(router.urls)),
]