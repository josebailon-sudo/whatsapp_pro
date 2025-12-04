from django.urls import path
from . import views
from . import subscription_views

urlpatterns = [
    path('', views.index, name='index'),
    path('wizard/', views.wizard_welcome, name='wizard_welcome'),
    path('wizard/step1/', views.wizard_step1_contacts, name='wizard_step1'),
    path('wizard/step2/', views.wizard_step2_message, name='wizard_step2'),
    path('wizard/step3/', views.wizard_step3_whatsapp, name='wizard_step3'),
    path('wizard/step4/', views.wizard_step4_preview, name='wizard_step4'),
    path('wizard/launch/<int:campaign_id>/', views.wizard_launch, name='wizard_launch'),
    
    path('contacts/', views.contacts_list, name='contacts_list'),
    path('contacts/create/', views.contact_create, name='contact_create'),
    path('contacts/<int:pk>/edit/', views.contact_edit, name='contact_edit'),
    path('contacts/<int:pk>/delete/', views.contact_delete, name='contact_delete'),
    path('contacts/import/', views.contacts_import, name='contacts_import'),
    path('contacts/delete-all/', views.contacts_delete_all, name='contacts_delete_all'),
    path('contacts/save-group/', views.contacts_save_group, name='contacts_save_group'),
    path('contacts/delete-group/', views.contacts_delete_group, name='contacts_delete_group'),
    path('templates/', views.templates_list, name='templates_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:pk>/edit/', views.template_edit, name='template_edit'),
    path('templates/<int:pk>/delete/', views.template_delete, name='template_delete'),
    path('campaigns/', views.campaigns_list, name='campaigns_list'),
    path('campaigns/create/', views.campaign_create, name='campaign_create'),
    path('campaigns/quick-send/', views.quick_send, name='quick_send'),
    path('campaigns/<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('campaigns/<int:pk>/send/', views.campaign_send, name='campaign_send'),
    
    # Tags
    path('tags/', views.tags_list, name='tags_list'),
    path('tags/<int:pk>/', views.tag_detail, name='tag_detail'),
    
    # Rules
    path('rules/', views.rules_list, name='rules_list'),
    path('rules/<int:pk>/', views.rule_detail, name='rule_detail'),
    
    # Workflows
    path('workflows/', views.workflows_list, name='workflows_list'),
    path('workflows/<int:pk>/', views.workflow_detail, name='workflow_detail'),
    
    # Follow-ups
    path('followups/', views.followups_list, name='followups_list'),
    path('followups/<int:pk>/', views.followup_detail, name='followup_detail'),
    
    # Attachments
    path('attachments/', views.attachments_list, name='attachments_list'),
    
    # Analytics
    path('analytics/', views.analytics, name='analytics'),
    
    # WhatsApp Connection
    path('whatsapp/connection/', views.whatsapp_connection, name='whatsapp_connection'),
    path('whatsapp/status/', views.whatsapp_status, name='whatsapp_status'),
    path('whatsapp/logout/', views.whatsapp_logout, name='whatsapp_logout'),
    
    # Subscription
    path('subscription/status/', subscription_views.subscription_status, name='subscription_status'),
    path('subscription/activate/', subscription_views.subscription_activate, name='subscription_activate'),
    path('subscription/payment/', subscription_views.subscription_payment_instructions, name='subscription_payment'),
]
