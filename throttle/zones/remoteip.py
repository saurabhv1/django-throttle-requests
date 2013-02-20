class RemoteIP:
    def __init__(self, **config):
        pass

    def process_view(self, request, view_func, view_args, view_kwargs):
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', "") or request.META.get('REMOTE_ADDR')
        return ip_address
