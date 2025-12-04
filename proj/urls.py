from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import routers
from whatsapp import api

router = routers.DefaultRouter()
router.register(r'contacts', api.ContactViewSet, basename='contacts')
router.register(r'templates', api.TemplateViewSet, basename='templates')
router.register(r'campaigns', api.CampaignViewSet, basename='campaigns')
router.register(r'messages', api.OutgoingMessageViewSet, basename='messages')
router.register(r'tags', api.TagViewSet, basename='tags')
router.register(r'rules', api.RuleViewSet, basename='rules')
router.register(r'workflows', api.WorkflowViewSet, basename='workflows')
router.register(r'followups', api.FollowUpViewSet, basename='followups')
router.register(r'attachments', api.AttachmentViewSet, basename='attachments')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('', include('whatsapp.urls')),  # web UI
]

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
