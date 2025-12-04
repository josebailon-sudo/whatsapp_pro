from django.core.management.base import BaseCommand
import pandas as pd
from whatsapp.models import Contact
from whatsapp.utils import limpiar_telefono
import sys

class Command(BaseCommand):
    help = 'Import contacts from CSV/Excel. Usage: python manage.py import_contacts path/to/file.csv'

    def add_arguments(self, parser):
        parser.add_argument('path', type=str)

    def handle(self, *args, **options):
        path = options['path']
        try:
            if path.endswith('.csv'):
                df = pd.read_csv(path)
            else:
                df = pd.read_excel(path, engine='openpyxl')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading file: {e}'))
            return

        name_col = next((c for c in df.columns if 'name' in c.lower() or 'nombre' in c.lower()), df.columns[0])
        phone_col = next((c for c in df.columns if any(x in c.lower() for x in ['phone','telefono','cel'])), df.columns[1])
        added = 0
        for _, row in df.iterrows():
            try:
                name = str(row[name_col]).strip()
                phone_raw = str(row[phone_col]).strip()
                phone = limpiar_telefono(phone_raw)
                if phone:
                    Contact.objects.update_or_create(phone=phone, defaults={'name': name, 'group': (row.get('group') if 'group' in row else 'General')})
                    added += 1
            except Exception:
                continue
        self.stdout.write(self.style.SUCCESS(f'Imported/updated {added} contacts'))
