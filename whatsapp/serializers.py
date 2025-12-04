from rest_framework import serializers
from .models import (
    Contact, Template, Campaign, OutgoingMessage,
    Tag, Rule, Workflow, FollowUp, Attachment
)

class TagSerializer(serializers.ModelSerializer):
    contact_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Tag
        fields = '__all__'

class ContactSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Tag.objects.all(), 
        source='tags', 
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Contact
        fields = '__all__'

class TemplateSerializer(serializers.ModelSerializer):
    variables_used = serializers.ListField(read_only=True)
    
    class Meta:
        model = Template
        fields = '__all__'

class CampaignSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    success_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Campaign
        fields = '__all__'

class OutgoingMessageSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source='contact.name', read_only=True)
    contact_phone = serializers.CharField(source='contact.phone', read_only=True)
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    
    class Meta:
        model = OutgoingMessage
        fields = '__all__'

class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rule
        fields = '__all__'

class WorkflowSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    trigger_display = serializers.CharField(source='get_trigger_display', read_only=True)
    
    class Meta:
        model = Workflow
        fields = '__all__'

class FollowUpSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source='contact.name', read_only=True)
    contact_phone = serializers.CharField(source='contact.phone', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = FollowUp
        fields = '__all__'

class AttachmentSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Tag.objects.all(), 
        source='tags', 
        write_only=True,
        required=False
    )
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = Attachment
        fields = '__all__'
