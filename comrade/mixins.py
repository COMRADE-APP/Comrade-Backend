"""
Input sanitization mixin to prevent XSS (Cross-Site Scripting) attacks.
Uses Mozilla's Bleach library to sanitize HTML input in text fields.
"""
import bleach
from rest_framework import serializers


class SanitizeHtmlMixin:
    """
    Mixin for DRF serializers that automatically sanitizes all string fields.
    Strips dangerous HTML tags while allowing safe ones if needed.
    """
    
    # Optional: Define fields that should NOT be sanitized (e.g. passwords)
    skip_sanitization_fields = ('password', 'token', 'secret')
    
    # Allowed HTML tags and attributes (default is very strict — allow nothing)
    allowed_tags = []
    allowed_attributes = {}

    def validate(self, attrs):
        """Sanitize all string fields in the serializer data."""
        sanitized_attrs = {}
        for key, value in attrs.items():
            if key in self.skip_sanitization_fields:
                sanitized_attrs[key] = value
                continue
                
            if isinstance(value, str):
                # Clean the HTML content
                cleaned_value = bleach.clean(
                    value,
                    tags=self.allowed_tags,
                    attributes=self.allowed_attributes,
                    strip=True
                )
                sanitized_attrs[key] = cleaned_value
            else:
                sanitized_attrs[key] = value
                
        return super().validate(sanitized_attrs)


class RichTextSanitizeMixin(SanitizeHtmlMixin):
    """
    Sanitization mixin for rich text editors (e.g., articles, complex descriptions).
    Allows safe formatting tags but strictly blocks scripts and iframes.
    """
    allowed_tags = [
        'p', 'b', 'i', 'strong', 'em', 'u', 'strike',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'br', 'hr',
        'a', 'img', 'blockquote', 'code', 'pre', 'span', 'div'
    ]
    allowed_attributes = {
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        '*': ['class', 'style']
    }
