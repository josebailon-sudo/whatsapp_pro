from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter para acceder a valores de diccionario usando claves dinámicas.
    Uso: {{ mydict|get_item:mykey }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key, '')
