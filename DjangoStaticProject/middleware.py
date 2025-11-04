class NgrokMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Add header to bypass ngrok warning
        response['ngrok-skip-browser-warning'] = 'anyvalue'
        return response