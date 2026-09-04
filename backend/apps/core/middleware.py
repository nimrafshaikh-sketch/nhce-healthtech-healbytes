import os

from django.http import HttpResponse

# Default: local Vite dev server only. Override with a comma-separated list
# via CORS_ALLOWED_ORIGINS for any other deployment.
_DEFAULT_ALLOWED_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


class SimpleCorsMiddleware:
    """Lightweight CORS middleware allowing an explicit, env-configurable
    allow-list of frontend origins to communicate with the Django backend
    API. Deliberately never uses `Access-Control-Allow-Origin: *` - this API
    authenticates with Bearer JWTs sent via the Authorization header, and a
    wildcard origin combined with `Access-Control-Allow-Headers:
    Authorization` would let any third-party page's script read responses
    from any request it can get a token attached to. Instead, the Origin
    header is checked against an allow-list and echoed back only on a match
    (with `Vary: Origin`), which is the standard safe pattern for
    credentialed/header-bearing cross-origin APIs.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        configured = os.environ.get("CORS_ALLOWED_ORIGINS", _DEFAULT_ALLOWED_ORIGINS)
        self.allowed_origins = {origin.strip() for origin in configured.split(",") if origin.strip()}

    def __call__(self, request):
        origin = request.META.get("HTTP_ORIGIN")

        if request.method == "OPTIONS":
            response = HttpResponse()
        else:
            response = self.get_response(request)

        if origin and origin in self.allowed_origins:
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        return response
