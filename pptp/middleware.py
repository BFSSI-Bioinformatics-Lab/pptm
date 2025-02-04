class CSRFDebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("CSRF Token in request:", request.META.get('HTTP_X_CSRFTOKEN'))
        print("CSRF Cookie:", request.COOKIES.get('csrftoken'))
        response = self.get_response(request)
        return response
