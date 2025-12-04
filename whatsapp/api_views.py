"""
WhatsApp Pro - API Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction

from .models import Contact, Template, Campaign, OutgoingMessage
from .serializers import (
    ContactSerializer, TemplateSerializer,
    CampaignSerializer, OutgoingMessageSerializer
)


class ContactViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing contacts.
    """
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    filterset_fields = ['opt_in', 'tags']
    search_fields = ['name', 'phone_number', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']


class TemplateViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing templates.
    """
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    search_fields = ['name', 'description', 'content']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """
        Preview template with sample contact data.
        """
        template = self.get_object()
        contact_id = request.data.get('contact_id')
        
        if contact_id:
            try:
                contact = Contact.objects.get(pk=contact_id)
                rendered = template.render(contact)
                return Response({'preview': rendered})
            except Contact.DoesNotExist:
                return Response(
                    {'error': 'Contact not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Sample preview
            sample_contact = Contact(
                name='Juan Pérez',
                phone_number='+1234567890',
                email='juan@example.com'
            )
            rendered = template.render(sample_contact)
            return Response({'preview': rendered})


class CampaignViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing campaigns.
    """
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    filterset_fields = ['status', 'template']
    search_fields = ['name', 'filter_tags']
    ordering_fields = ['name', 'created_at', 'scheduled_at']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'])
    def enqueue(self, request, pk=None):
        """
        Enqueue messages for this campaign.
        """
        campaign = self.get_object()
        
        if campaign.status == 'completed':
            return Response(
                {'error': 'Campaign already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if campaign.status == 'cancelled':
            return Response(
                {'error': 'Campaign is cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get target contacts
        contacts = campaign.get_target_contacts()
        
        if not contacts.exists():
            return Response(
                {'error': 'No contacts found matching campaign criteria'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create outgoing messages
        messages_created = 0
        with transaction.atomic():
            for contact in contacts:
                # Check if message already exists for this campaign and contact
                if not OutgoingMessage.objects.filter(
                    campaign=campaign,
                    contact=contact
                ).exists():
                    content = campaign.template.render(contact)
                    OutgoingMessage.objects.create(
                        campaign=campaign,
                        contact=contact,
                        content=content,
                        status='pending'
                    )
                    messages_created += 1
            
            # Update campaign status
            if campaign.status == 'draft':
                campaign.status = 'scheduled'
                campaign.save()
        
        return Response({
            'success': True,
            'messages_created': messages_created,
            'total_contacts': contacts.count()
        })

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        Get campaign statistics.
        """
        campaign = self.get_object()
        messages = campaign.messages.all()
        
        stats = {
            'total': messages.count(),
            'pending': messages.filter(status='pending').count(),
            'sent': messages.filter(status='sent').count(),
            'delivered': messages.filter(status='delivered').count(),
            'read': messages.filter(status='read').count(),
            'failed': messages.filter(status='failed').count(),
        }
        
        return Response(stats)


class OutgoingMessageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for outgoing messages.
    """
    queryset = OutgoingMessage.objects.all()
    serializer_class = OutgoingMessageSerializer
    filterset_fields = ['status', 'campaign', 'contact']
    search_fields = ['content', 'contact__name', 'contact__phone_number']
    ordering_fields = ['created_at', 'sent_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Optionally filter by campaign or contact.
        """
        queryset = super().get_queryset()
        
        # Allow filtering pending messages
        pending_only = self.request.query_params.get('pending_only', None)
        if pending_only == 'true':
            queryset = queryset.filter(status='pending')
        
        return queryset
