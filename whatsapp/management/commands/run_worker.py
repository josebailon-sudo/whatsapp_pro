from django.core.management.base import BaseCommand
import time
from whatsapp.models import OutgoingMessage, Campaign
from whatsapp.send_adapter import send_message
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Worker que procesa OutgoingMessage pendientes con configuración de velocidad y pausas.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Worker iniciado...'))
        self.stdout.write('Esperando mensajes pendientes...\n')
        
        try:
            while True:
                # Obtener campañas activas (sending)
                active_campaigns = Campaign.objects.filter(status='sending')
                
                if not active_campaigns.exists():
                    time.sleep(2)
                    continue
                
                for campaign in active_campaigns:
                    # Procesar mensajes de esta campaña
                    pending = OutgoingMessage.objects.filter(
                        campaign=campaign,
                        status='pending'
                    ).order_by('created_at', 'line_number')[:campaign.batch_size]
                    
                    if not pending.exists():
                        # No hay más mensajes pendientes, marcar campaña como completada
                        campaign.status = 'completed'
                        campaign.save()
                        self.stdout.write(self.style.SUCCESS(
                            f'✅ Campaña "{campaign.name}" completada!'
                        ))
                        continue
                    
                    # Procesar bloque de mensajes
                    batch_count = 0
                    for msg in pending:
                        try:
                            msg.status = 'sending'
                            msg.attempts += 1
                            msg.save()
                            
                            # Enviar mensaje (con adjunto si existe)
                            success, info = send_message(
                                msg.contact.phone, 
                                msg.payload,
                                attachment_path=msg.attachment_path,
                                attachment_type=msg.attachment_type
                            )
                            
                            if success:
                                msg.status = 'sent'
                                msg.sent_at = timezone.now()
                                msg.last_error = ''
                                campaign.sent_count += 1
                                
                                # Indicar si es multi-línea
                                line_info = f" [Línea {msg.line_number}]" if msg.line_number > 0 else ""
                                attach_info = f" 📎 {msg.attachment_type}" if msg.attachment_path else ""
                                
                                self.stdout.write(self.style.SUCCESS(
                                    f'✓ {msg.contact.name} ({msg.contact.phone}){line_info}{attach_info}'
                                ))
                            else:
                                msg.status = 'failed'
                                msg.last_error = info
                                campaign.failed_count += 1
                                self.stdout.write(self.style.ERROR(
                                    f'✗ {msg.contact.name}: {info}'
                                ))
                            
                            msg.save()
                            campaign.save()
                            
                            batch_count += 1
                            
                            # Delay entre mensajes según configuración
                            # Si es multi-línea del mismo contacto, delay más corto
                            if msg.line_number > 0:
                                time.sleep(min(campaign.delay_between_messages, 2.0))  # Máximo 2 segundos entre líneas
                            else:
                                time.sleep(campaign.delay_between_messages)
                            
                        except Exception as e:
                            msg.status = 'failed'
                            msg.last_error = str(e)
                            msg.save()
                            campaign.failed_count += 1
                            campaign.save()
                            self.stdout.write(self.style.ERROR(
                                f'✗ Error: {str(e)}'
                            ))
                    
                    # Pausa entre bloques si procesamos el tamaño completo del batch
                    if batch_count >= campaign.batch_size:
                        self.stdout.write(self.style.WARNING(
                            f'⏸️  Pausa de {campaign.delay_between_batches}s entre bloques...'
                        ))
                        time.sleep(campaign.delay_between_batches)
                    else:
                        # Si el batch fue más pequeño, esperar menos
                        time.sleep(2)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n⏹️  Worker detenido por el usuario.'))
