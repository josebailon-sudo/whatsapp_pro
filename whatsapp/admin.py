from django.contrib import admin
from django.utils import timezone
from .models import (
    Contact, Template, Campaign, OutgoingMessage, 
    Tag, Rule, Workflow, FollowUp, Attachment,
    Subscription, Payment
)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'created_at')
    search_fields = ('name',)

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name','phone','group','opt_in','last_interaction')
    list_filter = ('opt_in', 'group', 'tags')
    search_fields = ('name', 'phone')
    filter_horizontal = ('tags',)

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('name','category','active','created_at')
    list_filter = ('active', 'category')
    search_fields = ('name', 'content')

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name','template','scheduled_for','total_contacts','sent_count','created_at')
    list_filter = ('created_at',)
    search_fields = ('name',)

@admin.register(OutgoingMessage)
class OutgoingMessageAdmin(admin.ModelAdmin):
    list_display = ('campaign','contact','status','attempts','created_at','sent_at')
    list_filter = ('status',)
    search_fields = ('contact__phone', 'contact__name')

@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'priority', 'active', 'schedule_start', 'schedule_end')
    list_filter = ('active',)
    ordering = ('priority',)

@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('name', 'trigger', 'active', 'template', 'delay_minutes')
    list_filter = ('active', 'trigger')

@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ('contact', 'type', 'status', 'scheduled_for', 'is_overdue')
    list_filter = ('status', 'type')
    search_fields = ('contact__name', 'contact__phone', 'description')

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'type', 'size', 'uploaded_at')
    list_filter = ('type',)
    filter_horizontal = ('tags',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'plan', 'days_remaining', 'has_paid_initial', 'total_paid', 'is_active')
    list_filter = ('status', 'plan', 'has_paid_initial', 'is_active')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('trial_started', 'created_at', 'updated_at', 'days_remaining')
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user',)
        }),
        ('Estado', {
            'fields': ('status', 'plan', 'is_active', 'has_paid_initial')
        }),
        ('Fechas - Prueba', {
            'fields': ('trial_started', 'trial_ends')
        }),
        ('Fechas - Período Actual', {
            'fields': ('current_period_start', 'current_period_end')
        }),
        ('Pagos', {
            'fields': ('total_paid',)
        }),
        ('Otros', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_initial_action', 'activate_monthly_action', 'suspend_action']
    
    def activate_initial_action(self, request, queryset):
        for subscription in queryset:
            subscription.activate_initial()
        self.message_user(request, f'{queryset.count()} suscripciones activadas (3 meses)')
    activate_initial_action.short_description = 'Activar plan inicial (3 meses - $45)'
    
    def activate_monthly_action(self, request, queryset):
        count = 0
        for subscription in queryset:
            try:
                subscription.activate_monthly()
                count += 1
            except ValueError:
                pass
        self.message_user(request, f'{count} suscripciones renovadas (1 mes)')
    activate_monthly_action.short_description = 'Renovar mensual ($15)'
    
    def suspend_action(self, request, queryset):
        for subscription in queryset:
            subscription.suspend()
        self.message_user(request, f'{queryset.count()} suscripciones suspendidas')
    suspend_action.short_description = 'Suspender suscripciones'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('subscription_user', 'amount', 'plan_type', 'payment_method', 'verified', 'created_at')
    list_filter = ('verified', 'payment_method', 'plan_type')
    search_fields = ('subscription__user__username', 'transaction_id')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Suscripción', {
            'fields': ('subscription',)
        }),
        ('Pago', {
            'fields': ('amount', 'plan_type', 'payment_method', 'transaction_id')
        }),
        ('Verificación', {
            'fields': ('verified', 'verified_by', 'verified_at', 'notes')
        }),
        ('Fechas', {
            'fields': ('created_at',)
        }),
    )
    
    actions = ['verify_and_activate']
    
    def subscription_user(self, obj):
        return obj.subscription.user.username
    subscription_user.short_description = 'Usuario'
    
    def verify_and_activate(self, request, queryset):
        """Verifica el pago y activa la suscripción automáticamente"""
        count = 0
        for payment in queryset.filter(verified=False):
            payment.verified = True
            payment.verified_by = request.user.username
            payment.verified_at = timezone.now()
            payment.save()
            
            # Activar según el tipo de plan
            if payment.plan_type == 'initial':
                payment.subscription.activate_initial()
            elif payment.plan_type == 'monthly':
                payment.subscription.activate_monthly()
            
            count += 1
        
        self.message_user(request, f'{count} pagos verificados y suscripciones activadas')
    verify_and_activate.short_description = 'Verificar pago y activar suscripción'
