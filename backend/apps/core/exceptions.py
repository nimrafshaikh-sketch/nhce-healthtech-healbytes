from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Wraps DRF's default handler to produce a consistent error envelope:
    { "detail": "...", "code": "..." }
    """
    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data
        code = getattr(exc, "default_code", exc.__class__.__name__)
        response.data = {"detail": detail, "code": code}
    return response
