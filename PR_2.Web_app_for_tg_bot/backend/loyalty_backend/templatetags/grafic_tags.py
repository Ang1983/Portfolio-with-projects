from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if dictionary is None:
        return ''
    return dictionary.get(key, '')

@register.filter
def split_name(value):
    if not value:
        return ''
    parts = value.split(' ', 1)
    if len(parts) == 2:
        return mark_safe(f"{parts[0]}<br>{parts[1]}")
    return mark_safe(value)