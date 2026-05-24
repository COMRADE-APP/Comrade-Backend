from PIL import Image
import io
import os
from django.core.files.base import ContentFile


def convert_to_webp(image_file, quality=80):
    img = Image.open(image_file)
    img = img.convert('RGB')
    buffer = io.BytesIO()
    img.save(buffer, format='WEBP', quality=quality)
    filename = os.path.splitext(image_file.name)[0] + '.webp'
    return ContentFile(buffer.getvalue(), name=filename)


def generate_thumbnail(image_file, size=(200, 200), quality=60):
    img = Image.open(image_file)
    img = img.convert('RGB')
    img.thumbnail(size)
    buffer = io.BytesIO()
    img.save(buffer, format='WEBP', quality=quality)
    filename = f'thumb_{os.path.splitext(image_file.name)[0]}.webp'
    return ContentFile(buffer.getvalue(), name=filename)


def get_media_type(content_type):
    if content_type.startswith('image/'):
        if 'gif' in content_type:
            return 'gif'
        return 'image'
    if content_type.startswith('video/'):
        return 'video'
    return 'file'
