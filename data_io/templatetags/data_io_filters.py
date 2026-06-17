from django import template

register = template.Library()

@register.filter(name='replace_char')
def replace_char(value, args):
    if not value:
        return ""
    # Parse argument, e.g. "_, " meaning replace "_" with " " (we split by comma)
    parts = args.split(',')
    old = parts[0]
    new = parts[1] if len(parts) > 1 else ""
    return str(value).replace(old, new)
