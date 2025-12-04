"""
WhatsApp Pro - API URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api_views import (
    ContactViewSet, TemplateViewSet,
    CampaignViewSet, OutgoingMessageViewSet
)

router = DefaultRouter()
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'templates', TemplateViewSet, basename='template')
router.register(r'campaigns', CampaignViewSet, basename='campaign')
router.register(r'messages', OutgoingMessageViewSet, basename='message')

urlpatterns = [
    path('', include(router.urls)),
]
