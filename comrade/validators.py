"""
Global file upload validators for the Qomrade platform.
Applied to all FileField and ImageField instances to prevent
malicious file uploads (executables, scripts, polyglots).
"""
import os
from django.core.exceptions import ValidationError


# ── Allowed MIME types by category ────────────────────────────────────────────
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'}
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.webm', '.mkv'}
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.m4a', '.aac'}

ALL_ALLOWED_EXTENSIONS = (
    ALLOWED_IMAGE_EXTENSIONS |
    ALLOWED_DOCUMENT_EXTENSIONS |
    ALLOWED_VIDEO_EXTENSIONS |
    ALLOWED_AUDIO_EXTENSIONS
)

# Explicitly dangerous extensions that must NEVER be accepted
BLOCKED_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.com', '.msi', '.scr', '.pif',
    '.ps1', '.psm1', '.vbs', '.vbe', '.js', '.jse', '.wsf', '.wsh',
    '.sh', '.bash', '.csh', '.ksh',
    '.app', '.action', '.command',
    '.dll', '.so', '.dylib',
    '.php', '.asp', '.aspx', '.jsp', '.py', '.rb', '.pl',
    '.html', '.htm', '.xhtml', '.shtml',  # Prevent stored XSS
    '.svg',  # SVG can contain embedded JS — only allow via ImageField validator
    '.jar', '.class', '.war',
    '.reg', '.inf', '.lnk',
}

# Maximum file sizes per category (in bytes)
MAX_IMAGE_SIZE = 10 * 1024 * 1024      # 10 MB
MAX_DOCUMENT_SIZE = 25 * 1024 * 1024   # 25 MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024     # 100 MB
MAX_AUDIO_SIZE = 50 * 1024 * 1024      # 50 MB
MAX_GENERAL_SIZE = 25 * 1024 * 1024    # 25 MB default


def validate_file_extension(value):
    """
    Validates that the uploaded file has a safe extension.
    Blocks executables, scripts, and web files that could enable XSS.
    """
    ext = os.path.splitext(value.name)[1].lower()

    if ext in BLOCKED_EXTENSIONS:
        raise ValidationError(
            f"File type '{ext}' is not allowed. Executable and script files are blocked for security."
        )

    if ext and ext not in ALL_ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"File type '{ext}' is not supported. Allowed types: images, documents, videos, and audio files."
        )


def validate_file_size(value):
    """Validates the uploaded file does not exceed the size limit."""
    ext = os.path.splitext(value.name)[1].lower()

    if ext in ALLOWED_IMAGE_EXTENSIONS:
        max_size = MAX_IMAGE_SIZE
        label = "10 MB"
    elif ext in ALLOWED_VIDEO_EXTENSIONS:
        max_size = MAX_VIDEO_SIZE
        label = "100 MB"
    elif ext in ALLOWED_AUDIO_EXTENSIONS:
        max_size = MAX_AUDIO_SIZE
        label = "50 MB"
    else:
        max_size = MAX_DOCUMENT_SIZE
        label = "25 MB"

    if value.size > max_size:
        raise ValidationError(
            f"File size ({value.size / (1024*1024):.1f} MB) exceeds the maximum allowed size of {label}."
        )


def validate_image_file(value):
    """Strict validator for ImageField — only image extensions."""
    ext = os.path.splitext(value.name)[1].lower()
    # Allow SVG for images specifically but strip .svg from blocked list
    allowed = ALLOWED_IMAGE_EXTENSIONS
    if ext not in allowed:
        raise ValidationError(
            f"Only image files are allowed ({', '.join(sorted(allowed))}). Got: '{ext}'"
        )
    validate_file_size(value)


def validate_document_file(value):
    """Strict validator for document uploads (PDFs, Office files)."""
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError(
            f"Only document files are allowed ({', '.join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))}). Got: '{ext}'"
        )
    validate_file_size(value)


def validate_video_file(value):
    """Strict validator for video uploads."""
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise ValidationError(
            f"Only video files are allowed ({', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}). Got: '{ext}'"
        )
    validate_file_size(value)
