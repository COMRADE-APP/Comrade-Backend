from rest_framework.renderers import BaseRenderer

import base64

class PDFRenderer(BaseRenderer):
    media_type = 'application/pdf'
    format = 'pdf'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if isinstance(data, dict) and 'content_base64' in data:
            return base64.b64decode(data['content_base64'])
        return data