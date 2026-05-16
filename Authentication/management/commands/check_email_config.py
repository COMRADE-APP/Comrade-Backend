from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import traceback

class Command(BaseCommand):
    help = 'Tests the email configuration by sending a test email'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='The email address to send the test message to')

    def handle(self, *args, **options):
        target_email = options['email']
        
        self.stdout.write(self.style.NOTICE(f"Testing email configuration..."))
        self.stdout.write(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"EMAIL_HOST: {settings.EMAIL_HOST}")
        self.stdout.write(f"EMAIL_PORT: {settings.EMAIL_PORT}")
        self.stdout.write(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        
        try:
            sent = send_mail(
                subject='Qomrade Platform - Email Health Check',
                message='If you are reading this, the Qomrade Platform email configuration is working correctly.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[target_email],
                fail_silently=False,
            )
            
            if sent:
                self.stdout.write(self.style.SUCCESS(f"Successfully sent test email to {target_email}"))
            else:
                self.stdout.write(self.style.WARNING(f"send_mail returned {sent} (0 usually means failed silently or no connection)"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to send email: {str(e)}"))
            self.stdout.write(traceback.format_exc())
