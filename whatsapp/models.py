from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import json

class Subscription(models.Model):
    """Sistema de suscripciones y licencias"""
    STATUS_CHOICES = [
        ('trial', 'Prueba Gratuita (30 días)'),
        ('active', 'Activa'),
        ('expired', 'Vencida'),
        ('suspended', 'Suspendida'),
    ]
    
    PLAN_CHOICES = [
        ('trial', 'Prueba - 30 días gratis'),
        ('initial', 'Activación Inicial - 3 meses ($45)'),
        ('monthly', 'Mensual - $15/mes'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    
    # Estado de la suscripción
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='trial')
    
    # Fechas
    trial_started = models.DateTimeField(auto_now_add=True)
    trial_ends = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    
    # Pagos
    has_paid_initial = models.BooleanField(default=False)  # Si pagó los 3 meses iniciales
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Control
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        # Auto-configurar trial_ends al crear
        if not self.trial_ends and self.status == 'trial':
            self.trial_ends = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)
    
    @property
    def days_remaining(self):
        """Días restantes de la suscripción actual"""
        if self.status == 'trial' and self.trial_ends:
            delta = self.trial_ends - timezone.now()
            return max(0, delta.days)
        elif self.current_period_end:
            delta = self.current_period_end - timezone.now()
            return max(0, delta.days)
        return 0
    
    @property
    def is_expired(self):
        """Verifica si la suscripción está vencida"""
        if self.status == 'trial':
            return timezone.now() > self.trial_ends if self.trial_ends else False
        elif self.current_period_end:
            return timezone.now() > self.current_period_end
        return True
    
    def activate_initial(self):
        """Activa el plan inicial de 3 meses ($45)"""
        now = timezone.now()
        self.status = 'active'
        self.plan = 'initial'
        self.has_paid_initial = True
        self.current_period_start = now
        self.current_period_end = now + timedelta(days=90)  # 3 meses
        self.total_paid += 45
        self.is_active = True
        self.save()
    
    def activate_monthly(self):
        """Activa renovación mensual ($15)"""
        if not self.has_paid_initial:
            raise ValueError("Debe activar primero el plan inicial de 3 meses")
        
        now = timezone.now()
        self.status = 'active'
        self.plan = 'monthly'
        self.current_period_start = now
        self.current_period_end = now + timedelta(days=30)
        self.total_paid += 15
        self.is_active = True
        self.save()
    
    def suspend(self):
        """Suspende la suscripción"""
        self.status = 'suspended'
        self.is_active = False
        self.save()
    
    def check_and_update_status(self):
        """Verifica y actualiza el estado automáticamente"""
        if self.is_expired and self.status != 'suspended':
            self.status = 'expired'
            self.is_active = False
            self.save()
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Suscripción'
        verbose_name_plural = 'Suscripciones'


class Payment(models.Model):
    """Registro de pagos"""
    PAYMENT_METHOD_CHOICES = [
        ('transfer', 'Transferencia Bancaria'),
        ('paypal', 'PayPal'),
        ('stripe', 'Tarjeta (Stripe)'),
        ('cash', 'Efectivo'),
        ('other', 'Otro'),
    ]
    
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    
    # Plan que se pagó
    plan_type = models.CharField(max_length=20, choices=Subscription.PLAN_CHOICES)
    
    # Detalles
    transaction_id = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    
    # Verificación
    verified = models.BooleanField(default=False)
    verified_by = models.CharField(max_length=150, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.subscription.user.username} - ${self.amount} ({self.get_plan_type_display()})"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'


class Tag(models.Model):
    """Etiquetas para categorizar contactos"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#3498DB')  # Hex color
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class Contact(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=32, unique=True)
    email = models.EmailField(max_length=254, blank=True, default='')
    group = models.CharField(max_length=100, blank=True, default='General')
    opt_in = models.BooleanField(default=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='contacts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Campos adicionales del proyecto Tkinter
    notes = models.TextField(blank=True)
    last_interaction = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"
    
    class Meta:
        ordering = ['name']

class Template(models.Model):
    """Plantillas de mensajes con variables dinámicas"""
    name = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=100, default='General')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Campos avanzados del sistema de plantillas
    variables_used = models.JSONField(default=list, blank=True)  # ['nombre', 'telefono', etc]
    preview_sample = models.TextField(blank=True)

    def __str__(self):
        return self.name
    
    def extract_variables(self):
        """Extrae variables del contenido {variable}"""
        import re
        return list(set(re.findall(r'\{(\w+)\}', self.content)))
    
    def save(self, *args, **kwargs):
        self.variables_used = self.extract_variables()
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']

class Campaign(models.Model):
    name = models.CharField(max_length=200)
    template = models.ForeignKey(Template, on_delete=models.PROTECT, null=True, blank=True)  # null para envíos rápidos
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=150, default='admin')
    
    # Estadísticas
    total_contacts = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    
    # Configuración de envío
    send_speed = models.IntegerField(default=10)  # mensajes por minuto
    batch_size = models.IntegerField(default=50)  # mensajes por bloque
    delay_between_batches = models.IntegerField(default=60)  # segundos entre bloques
    delay_between_messages = models.FloatField(default=6.0)  # segundos entre mensajes
    
    # Estado del envío
    status = models.CharField(max_length=20, default='draft', choices=[
        ('draft', 'Borrador'),
        ('ready', 'Listo'),
        ('sending', 'Enviando'),
        ('paused', 'Pausado'),
        ('completed', 'Completado'),
        ('failed', 'Fallido')
    ])
    
    def __str__(self):
        return self.name
    
    @property
    def success_rate(self):
        if self.total_contacts == 0:
            return 0
        return (self.sent_count / self.total_contacts) * 100
    
    class Meta:
        ordering = ['-created_at']

class OutgoingMessage(models.Model):
    STATUS_CHOICES = [('pending','pending'), ('sending','sending'), ('sent','sent'), ('failed','failed'), ('cancelled','cancelled')]
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='messages')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    payload = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attempts = models.IntegerField(default=0)
    last_error = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Soporte para archivos adjuntos
    attachment_path = models.CharField(max_length=500, blank=True, null=True)
    attachment_type = models.CharField(max_length=50, blank=True, null=True)  # image, document, video, audio
    attachment_caption = models.TextField(blank=True, null=True)  # Caption para imágenes/videos
    
    # Para envíos multi-línea (cada línea como mensaje separado)
    line_number = models.IntegerField(default=0)  # 0 = mensaje único, 1,2,3... = líneas separadas
    parent_message = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='line_messages')

    def __str__(self):
        return f"{self.contact.phone} - {self.status}"
    
    class Meta:
        ordering = ['-created_at', 'line_number']

class Rule(models.Model):
    """Reglas de respuestas automáticas"""
    name = models.CharField(max_length=200)
    priority = models.IntegerField(default=999)  # 1 = máxima prioridad
    active = models.BooleanField(default=True)
    
    # Condiciones (JSON): [{'type': 'contains', 'value': 'hola'}]
    conditions = models.JSONField(default=list)
    
    # Respuesta automática
    response = models.TextField()
    
    # Horario (formato HH:MM)
    schedule_start = models.TimeField(default='00:00')
    schedule_end = models.TimeField(default='23:59')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} (Prioridad: {self.priority})"
    
    def matches(self, message_text):
        """Verifica si el mensaje cumple las condiciones"""
        from datetime import datetime
        
        # Verificar horario
        now_time = datetime.now().time()
        if not (self.schedule_start <= now_time <= self.schedule_end):
            return False
        
        # Verificar condiciones
        for condition in self.conditions:
            cond_type = condition.get('type', 'contains')
            value = condition.get('value', '').lower()
            msg_lower = message_text.lower()
            
            if cond_type == 'contains':
                if value not in msg_lower:
                    return False
            elif cond_type == 'starts_with':
                if not msg_lower.startswith(value):
                    return False
            elif cond_type == 'ends_with':
                if not msg_lower.endswith(value):
                    return False
        
        return True
    
    class Meta:
        ordering = ['priority', 'name']

class Workflow(models.Model):
    """Automatizaciones/Workflows"""
    TRIGGER_CHOICES = [
        ('on_respuesta', 'Al recibir respuesta'),
        ('on_mensaje_enviado', 'Al enviar mensaje'),
        ('on_import_contactos', 'Al importar contactos'),
    ]
    
    name = models.CharField(max_length=200)
    trigger = models.CharField(max_length=50, choices=TRIGGER_CHOICES)
    active = models.BooleanField(default=True)
    
    # Condición (texto que debe contener el mensaje)
    condition = models.CharField(max_length=500, blank=True)
    
    # Acción a ejecutar
    action = models.CharField(max_length=100, default='send_template')
    
    # Plantilla a enviar
    template = models.ForeignKey(Template, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Delay en minutos (0 = inmediato)
    delay_minutes = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_trigger_display()})"
    
    class Meta:
        ordering = ['name']

class FollowUp(models.Model):
    """Seguimientos/Recordatorios"""
    TYPE_CHOICES = [
        ('llamada', 'Llamada'),
        ('mensaje', 'Mensaje'),
        ('visita', 'Visita'),
        ('correo', 'Correo'),
        ('otro', 'Otro'),
    ]
    
    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('completado', 'Completado'),
        ('rechazado', 'Rechazado'),
        ('reprogramado', 'Reprogramado'),
    ]
    
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='followups')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendiente')
    
    scheduled_for = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.contact.name} - {self.get_type_display()} ({self.status})"
    
    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.status == 'pendiente' and self.scheduled_for < timezone.now()
    
    class Meta:
        ordering = ['scheduled_for']

class Attachment(models.Model):
    """Archivos adjuntos para mensajes"""
    TYPE_CHOICES = [
        ('image', 'Imagen'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('document', 'Documento'),
    ]
    
    file = models.FileField(upload_to='attachments/%Y/%m/')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    original_name = models.CharField(max_length=255)
    size = models.IntegerField()  # bytes
    
    # Opcionalmente asociar a etiquetas
    tags = models.ManyToManyField(Tag, blank=True, related_name='attachments')
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.original_name} ({self.get_type_display()})"
    
    class Meta:
        ordering = ['-uploaded_at']
