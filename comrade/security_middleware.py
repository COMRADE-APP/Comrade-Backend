"""
Security headers middleware for the Qomrade platform.
Adds Content-Security-Policy, X-Frame-Options, Permissions-Policy,
and other defense-in-depth headers to all HTTP responses.
"""


class SecurityHeadersMiddleware:
    """
    Adds security headers to all responses.
    Place after Django's SecurityMiddleware in MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # ── Content-Security-Policy ──────────────────────────────────────
        # Restricts where resources (scripts, styles, images) can be loaded from.
        # This prevents XSS by blocking inline scripts and unauthorized external sources.
        csp_directives = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: blob: https://*.supabase.co",
            "media-src 'self' blob: https://*.supabase.co",
            "connect-src 'self' https://*.supabase.co https://*.stripe.com wss://*",
            "frame-src 'self' https://*.stripe.com https://js.stripe.com",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        ]
        response["Content-Security-Policy"] = "; ".join(csp_directives)

        # ── X-Frame-Options ──────────────────────────────────────────────
        # Prevents clickjacking by blocking the page from being embedded in iframes.
        response["X-Frame-Options"] = "DENY"

        # ── X-Content-Type-Options ───────────────────────────────────────
        # Prevents browsers from MIME-sniffing the content type,
        # which could allow an attacker to serve a .jpg that's actually HTML/JS.
        response["X-Content-Type-Options"] = "nosniff"

        # ── Referrer-Policy ──────────────────────────────────────────────
        # Controls how much referrer information is sent with requests.
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # ── Permissions-Policy ───────────────────────────────────────────
        # Restricts which browser features can be used.
        response["Permissions-Policy"] = (
            "camera=(self), microphone=(self), geolocation=(self), "
            "payment=(self), usb=(), magnetometer=(), gyroscope=(), "
            "accelerometer=()"
        )

        # ── Cross-Origin headers ─────────────────────────────────────────
        response["Cross-Origin-Opener-Policy"] = "same-origin"

        return response


class FileUploadValidationMiddleware:
    """
    Globally intercepts all requests containing files and validates them
    against the allowed extensions and size limits before they reach any view.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in ["POST", "PUT", "PATCH"] and request.FILES:
            from comrade.validators import validate_file_extension, validate_file_size
            from django.core.exceptions import ValidationError
            from django.http import JsonResponse
            
            for field_name, file_list in request.FILES.lists():
                for file_obj in file_list:
                    try:
                        validate_file_extension(file_obj)
                        validate_file_size(file_obj)
                    except ValidationError as e:
                        return JsonResponse({
                            "error": "File validation failed",
                            "detail": e.messages[0],
                            "field": field_name
                        }, status=400)
                        
        return self.get_response(request)
