from django.core.management.base import BaseCommand
import json
from whatsapp.models import Template


class Command(BaseCommand):
    help = 'Importa plantillas desde plantillas.json del proyecto anterior'

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Ruta al archivo plantillas.json'
        )

    def handle(self, *args, **options):
        json_file = options['json_file']
        
        self.stdout.write(f'Leyendo plantillas desde: {json_file}')
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error leyendo archivo: {e}'))
            return
        
        added = 0
        updated = 0
        
        # Si el JSON es una lista de plantillas
        if isinstance(data, list):
            templates_list = data
        # Si el JSON es un dict con clave 'plantillas'
        elif isinstance(data, dict) and 'plantillas' in data:
            templates_list = data['plantillas']
        # Si el JSON es un dict donde cada key es el nombre
        elif isinstance(data, dict):
            templates_list = [
                {'nombre': k, 'contenido': v}
                for k, v in data.items()
            ]
        else:
            self.stdout.write(self.style.ERROR('Formato de JSON no reconocido'))
            return
        
        for item in templates_list:
            try:
                # Adaptarse a diferentes formatos de JSON
                name = item.get('nombre') or item.get('name') or item.get('titulo')
                content = item.get('contenido') or item.get('content') or item.get('texto')
                
                if not name or not content:
                    self.stdout.write(
                        self.style.WARNING(f'Plantilla sin nombre o contenido: {item}')
                    )
                    continue
                
                # Crear o actualizar plantilla
                template, created = Template.objects.update_or_create(
                    name=name,
                    defaults={
                        'content': content,
                        'active': True
                    }
                )
                
                if created:
                    added += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Creada: {name}')
                    )
                else:
                    updated += 1
                    self.stdout.write(
                        self.style.WARNING(f'↻ Actualizada: {name}')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error procesando {item}: {e}')
                )
                continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Completado: {added} creadas, {updated} actualizadas'
            )
        )
