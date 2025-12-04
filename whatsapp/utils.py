import re
from datetime import datetime
import random

def limpiar_telefono(phone, default_country='+593'):
    if not phone:
        return ''
    s = re.sub(r'[\s\(\)\-]', '', str(phone))
    if s.startswith('+'):
        return s
    if len(s) >= 9 and not s.startswith('0'):
        return default_country + s[-9:]
    return s

def extraer_variables(text):
    import re
    return list(set(re.findall(r'\{(\w+)\}', text)))

def process_template(template_text, contacto):
    saludo_choices = ['Dios te bendiga', 'Bendiciones', 'Hola']
    replacements = {
        'nombre': contacto.get('nombre', ''),
        'telefono': contacto.get('telefono', ''),
        'grupo': contacto.get('grupo', ''),
        'fecha': datetime.now().strftime('%d/%m/%Y'),
        'hora': datetime.now().strftime('%H:%M'),
        'saludo': random.choice(saludo_choices)
    }
    out = template_text
    for k,v in replacements.items():
        out = out.replace(f'{{{k}}}', str(v))
    return out
