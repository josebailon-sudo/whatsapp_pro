from django.core.management.base import BaseCommand
import json
from whatsapp.models import Campaign, Template
from django.utils import timezone
from datetime import datetime


class Command(BaseCommand):
    help = 'Importa workflows/campañas desde workflows.json del proyecto anterior'

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Ruta al archivo workflows.json'
        )

    def handle(self, *args, **options):
        json_file = options['json_file']
        
        self.stdout.write(f'Leyendo workflows desde: {json_file}')
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error leyendo archivo: {e}'))
            return
        
        added = 0
        skipped = 0
        
        # Si el JSON es una lista de workflows
        if isinstance(data, list):
            workflows_list = data
        # Si el JSON es un dict con clave 'workflows'
        elif isinstance(data, dict) and 'workflows' in data:
            workflows_list = data['workflows']
        # Si el JSON es un dict donde cada key es el ID
        elif isinstance(data, dict):
            workflows_list = list(data.values())
        else:
            self.stdout.write(self.style.ERROR('Formato de JSON no reconocido'))
            return
        
        for item in workflows_list:
            try:
                # Extraer campos del workflow
                name = item.get('nombre') or item.get('name') or f"Workflow {added+1}"
                template_name = item.get('plantilla') or item.get('template')
                programado = item.get('programado') or item.get('scheduled')
                
                # Buscar plantilla
                if template_name:
                    try:
                        template = Template.objects.get(name=template_name)
                    except Template.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f'⚠ Plantilla "{template_name}" no existe. '
                                f'Saltando workflow "{name}"'
                            )
                        )
                        skipped += 1
                        continue
                else:
                    # Si no hay plantilla, usar la primera disponible
                    template = Template.objects.filter(active=True).first()
                    if not template:
                        self.stdout.write(
                            self.style.ERROR('No hay plantillas activas. Crea una primero.')
                        )
                        return
                
                # Convertir fecha programada si existe
                scheduled_for = None
                if programado:
                    try:
                        # Intentar parsear diferentes formatos
                        if isinstance(programado, str):
                            scheduled_for = datetime.fromisoformat(programado)
                    except:
                        pass
                
                # Crear campaña
                campaign = Campaign.objects.create(
                    name=name,
                    template=template,
                    scheduled_for=scheduled_for,
                    created_by='imported'
                )
                
                added += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Creada campaña: {name} (plantilla: {template.name})'
                    )
                )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error procesando {item}: {e}')
                )
                continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Completado: {added} campañas creadas, {skipped} saltadas'
            )
        )
        
        if skipped > 0:
            self.stdout.write(
                self.style.WARNING(
                    '\nNota: Algunas campañas se saltaron porque sus plantillas no existen. '
                    'Importa las plantillas primero con: python manage.py import_plantillas'
                )
            )
