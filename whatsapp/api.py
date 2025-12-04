from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from .models import (
    Contact, Template, Campaign, OutgoingMessage,
    Tag, Rule, Workflow, FollowUp, Attachment
)
from .serializers import (
    ContactSerializer, TemplateSerializer, CampaignSerializer, 
    OutgoingMessageSerializer, TagSerializer, RuleSerializer,
    WorkflowSerializer, FollowUpSerializer, AttachmentSerializer
)
from .utils import process_template

class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.annotate(contact_count=Count('contacts')).order_by('name')
    serializer_class = TagSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']
    
    @action(detail=True, methods=['get'])
    def contacts(self, request, pk=None):
        """Obtener todos los contactos de una etiqueta"""
        tag = self.get_object()
        contacts = tag.contacts.all()
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)

class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all().order_by('name')
    serializer_class = ContactSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'phone', 'group']
    
    @action(detail=False, methods=['get'])
    def by_group(self, request):
        """Listar contactos agrupados por grupo"""
        groups = Contact.objects.values('group').annotate(count=Count('id')).order_by('-count')
        return Response(groups)
    
    @action(detail=True, methods=['post'])
    def add_tag(self, request, pk=None):
        """Agregar etiqueta a un contacto"""
        contact = self.get_object()
        tag_id = request.data.get('tag_id')
        if not tag_id:
            return Response({'error': 'tag_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            tag = Tag.objects.get(pk=tag_id)
            contact.tags.add(tag)
            return Response({'status': 'tag added'})
        except Tag.DoesNotExist:
            return Response({'error': 'Tag not found'}, status=status.HTTP_404_NOT_FOUND)

class TemplateViewSet(viewsets.ModelViewSet):
    queryset = Template.objects.all().order_by('-created_at')
    serializer_class = TemplateSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'content', 'category']
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Listar solo plantillas activas"""
        templates = Template.objects.filter(active=True)
        serializer = self.get_serializer(templates, many=True)
        return Response(serializer.data)

class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all().order_by('-created_at')
    serializer_class = CampaignSerializer

    @action(detail=True, methods=['post'])
    def enqueue(self, request, pk=None):
        """Encolar mensajes para todos los contactos opt-in"""
        try:
            campaign = self.get_object()
            contacts = Contact.objects.filter(opt_in=True)
            created = 0
            for c in contacts:
                payload = process_template(campaign.template.content, {'nombre': c.name, 'telefono': c.phone, 'grupo': c.group})
                OutgoingMessage.objects.create(campaign=campaign, contact=c, payload=payload)
                created += 1
            
            # Actualizar estadísticas
            campaign.total_contacts = created
            campaign.save()
            
            return Response({'enqueued': created})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Obtener estadísticas de la campaña"""
        campaign = self.get_object()
        messages = campaign.messages.all()
        stats = {
            'total': messages.count(),
            'pending': messages.filter(status='pending').count(),
            'sent': messages.filter(status='sent').count(),
            'failed': messages.filter(status='failed').count(),
            'success_rate': campaign.success_rate
        }
        return Response(stats)

class OutgoingMessageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OutgoingMessage.objects.all().order_by('-created_at')
    serializer_class = OutgoingMessageSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['contact__name', 'contact__phone']
    
    @action(detail=False, methods=['get'])
    def by_status(self, request):
        """Agrupar mensajes por estado"""
        by_status = OutgoingMessage.objects.values('status').annotate(count=Count('id'))
        return Response(by_status)

class RuleViewSet(viewsets.ModelViewSet):
    queryset = Rule.objects.all().order_by('priority', 'name')
    serializer_class = RuleSerializer
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Activar/desactivar regla"""
        rule = self.get_object()
        rule.active = not rule.active
        rule.save()
        return Response({'active': rule.active})
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Probar si un mensaje cumple las condiciones de la regla"""
        rule = self.get_object()
        message_text = request.data.get('message', '')
        matches = rule.matches(message_text)
        return Response({
            'matches': matches,
            'rule_name': rule.name,
            'response': rule.response if matches else None
        })

class WorkflowViewSet(viewsets.ModelViewSet):
    queryset = Workflow.objects.all().order_by('name')
    serializer_class = WorkflowSerializer
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Activar/desactivar workflow"""
        workflow = self.get_object()
        workflow.active = not workflow.active
        workflow.save()
        return Response({'active': workflow.active})
    
    @action(detail=False, methods=['get'])
    def by_trigger(self, request):
        """Listar workflows agrupados por disparador"""
        trigger = request.query_params.get('trigger')
        if trigger:
            workflows = Workflow.objects.filter(trigger=trigger, active=True)
            serializer = self.get_serializer(workflows, many=True)
            return Response(serializer.data)
        return Response({'error': 'trigger parameter required'}, status=status.HTTP_400_BAD_REQUEST)

class FollowUpViewSet(viewsets.ModelViewSet):
    queryset = FollowUp.objects.all().order_by('scheduled_for')
    serializer_class = FollowUpSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['contact__name', 'description']
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Marcar seguimiento como completado"""
        from django.utils import timezone
        followup = self.get_object()
        followup.status = 'completado'
        followup.completed_at = timezone.now()
        followup.save()
        return Response({'status': 'completed'})
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Listar seguimientos pendientes"""
        followups = FollowUp.objects.filter(status='pendiente')
        serializer = self.get_serializer(followups, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Listar seguimientos vencidos"""
        from django.utils import timezone
        followups = FollowUp.objects.filter(
            status='pendiente',
            scheduled_for__lt=timezone.now()
        )
        serializer = self.get_serializer(followups, many=True)
        return Response(serializer.data)

class AttachmentViewSet(viewsets.ModelViewSet):
    queryset = Attachment.objects.all().order_by('-uploaded_at')
    serializer_class = AttachmentSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['original_name']
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Listar archivos por tipo"""
        file_type = request.query_params.get('type')
        if file_type:
            attachments = Attachment.objects.filter(type=file_type)
            serializer = self.get_serializer(attachments, many=True)
            return Response(serializer.data)
        
        # Estadísticas por tipo
        by_type = Attachment.objects.values('type').annotate(count=Count('id'))
        return Response(by_type)
