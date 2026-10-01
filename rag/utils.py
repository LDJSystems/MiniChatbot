def get_client_ip(request):
    """Extrae la IP real desde el proxy inverso o hace fallback a REMOTE_ADDR."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')