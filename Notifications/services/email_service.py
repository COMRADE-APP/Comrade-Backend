"""
Email notification service for sending templated emails.
Uses Django's built-in email backend (configurable to SMTP/SendGrid/Gmail).
"""
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending templated transactional emails.
    """

    DEFAULT_FROM = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@qomrade.com')

    TEMPLATES = {
        'kyc_approved': {
            'subject': '✅ Your Identity Has Been Verified — Qomrade',
            'body': (
                "Hi {name},\n\n"
                "Great news! Your identity verification (KYC) has been approved.\n"
                "You now have full access to escrow, loans, and premium financial services on Qomrade.\n\n"
                "— The Qomrade Team"
            ),
        },
        'kyc_rejected': {
            'subject': '⚠️ Identity Verification Update — Qomrade',
            'body': (
                "Hi {name},\n\n"
                "Unfortunately, your identity verification was not approved.\n"
                "Reason: {reason}\n\n"
                "Please re-submit your documents from your account settings.\n\n"
                "— The Qomrade Team"
            ),
        },
        'payout_processed': {
            'subject': '💰 Payout Processed — Qomrade',
            'body': (
                "Hi {name},\n\n"
                "A payout of {amount} has been successfully processed to your {method} account.\n"
                "Transaction Reference: {reference}\n\n"
                "— The Qomrade Team"
            ),
        },
        'refund_issued': {
            'subject': '🔄 Refund Issued — Qomrade',
            'body': (
                "Hi {name},\n\n"
                "A refund of {amount} has been issued for transaction {reference}.\n"
                "Reason: {reason}\n\n"
                "The funds will be returned to your original payment method within 5-10 business days.\n\n"
                "— The Qomrade Team"
            ),
        },
        'loan_approved': {
            'subject': '✅ Loan Application Approved — Qomrade',
            'body': (
                "Hi {name},\n\n"
                "Your loan application for {amount} has been approved!\n"
                "The funds have been credited to your Qomrade wallet.\n\n"
                "Repayment begins on {due_date}.\n\n"
                "— The Qomrade Team"
            ),
        },
        'loan_overdue': {
            'subject': '⚠️ Loan Repayment Overdue — Qomrade',
            'body': (
                "Hi {name},\n\n"
                "Your loan repayment of {amount} was due on {due_date} and is now overdue.\n"
                "Please make a payment as soon as possible to avoid penalties.\n\n"
                "— The Qomrade Team"
            ),
        },
        'escrow_released': {
            'subject': '✅ Escrow Funds Released — Qomrade',
            'body': (
                "Hi {name},\n\n"
                "The escrow for \"{title}\" ({amount}) has been released.\n"
                "The funds are now available in your wallet.\n\n"
                "— The Qomrade Team"
            ),
        },
        'dispute_resolved': {
            'subject': '📋 Escrow Dispute Resolved — Qomrade',
            'body': (
                "Hi {name},\n\n"
                "The dispute for escrow \"{title}\" has been resolved.\n"
                "Resolution: {resolution}\n\n"
                "Log in to your account for full details.\n\n"
                "— The Qomrade Team"
            ),
        },
        'standing_order_failed': {
            'subject': '❌ Standing Order Failed — Qomrade',
            'body': (
                "Hi {name},\n\n"
                "Your standing order to {provider} for {amount} could not be processed due to insufficient balance.\n"
                "Please top up your wallet and retry.\n\n"
                "— The Qomrade Team"
            ),
        },
        # Provider notification templates
        'provider_app_submitted': {
            'subject': '📝 Application Submitted — {provider}',
            'body': (
                "Hi {name},\n\n"
                "Your application to {provider} has been submitted successfully.\n"
                "Service: {service_name}\n"
                "Application ID: {application_id}\n\n"
                "You'll be notified once the provider reviews your application.\n\n"
                "— The Qomrade Team"
            ),
        },
        'provider_app_approved': {
            'subject': '✅ Application Approved — {provider}',
            'body': (
                "Hi {name},\n\n"
                "Great news! Your application to {provider} has been APPROVED!\n"
                "Service: {service_name}\n"
                "Application ID: {application_id}\n\n"
                "You can now access and use this service. Log in to your dashboard to get started.\n\n"
                "— The Qomrade Team"
            ),
        },
        'provider_app_rejected': {
            'subject': '⚠️ Application Update — {provider}',
            'body': (
                "Hi {name},\n\n"
                "Unfortunately, your application to {provider} was not approved.\n"
                "Service: {service_name}\n"
                "Reason: {reason}\n\n"
                "You may submit a new application or contact the provider for more information.\n\n"
                "— The Qomrade Team"
            ),
        },
        'provider_app_changes': {
            'subject': '📋 Action Required — {provider}',
            'body': (
                "Hi {name},\n\n"
                "{provider} has requested changes to your application.\n"
                "Service: {service_name}\n"
                "Notes: {reason}\n\n"
                "Please log in to update your application and resubmit.\n\n"
                "— The Qomrade Team"
            ),
        },
        'provider_query_response': {
            'subject': '💬 Query Response — {provider}',
            'body': (
                "Hi {name},\n\n"
                "{provider} has responded to your query.\n"
                "Subject: {query_subject}\n"
                "Response: {response}\n\n"
                "Log in to view the full response and continue the conversation.\n\n"
                "— The Qomrade Team"
            ),
        },
        'provider_transaction': {
            'subject': '💳 Transaction Complete — {provider}',
            'body': (
                "Hi {name},\n\n"
                "Your transaction with {provider} has been completed.\n"
                "Amount: {amount}\n"
                "Reference: {reference}\n"
                "Status: Completed\n\n"
                "Thank you for using {provider} on Qomrade!\n\n"
                "— The Qomrade Team"
            ),
        },
        'welcome': {
            'subject': '🎉 Welcome to Qomrade!',
            'body': (
                "Hi {name},\n\n"
                "Welcome to Qomrade — your all-in-one platform for collaborative finance, research, and community.\n\n"
                "Get started by:\n"
                "1. Completing your profile\n"
                "2. Verifying your identity\n"
                "3. Exploring Payment Groups and the Marketplace\n\n"
                "— The Qomrade Team"
            ),
        },
    }

    @staticmethod
    def send(template_key, recipient_email, context=None, **kwargs):
        """
        Send a templated email.

        Args:
            template_key: Key from TEMPLATES dict (e.g. 'kyc_approved')
            recipient_email: Email address to send to
            context: Dict of template variables (e.g. {'name': 'John', 'amount': '5000'})
        """
        context = context or {}

        template = EmailService.TEMPLATES.get(template_key)
        if not template:
            logger.error(f"Email template '{template_key}' not found")
            return False

        subject = template['subject']
        body = template['body'].format(**context)

        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=EmailService.DEFAULT_FROM,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
            logger.info(f"Email '{template_key}' sent to {recipient_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email '{template_key}' to {recipient_email}: {e}")
            return False

    @staticmethod
    def send_raw(subject, body, recipient_email, from_email=None):
        """Send a raw (non-templated) email."""
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=from_email or EmailService.DEFAULT_FROM,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send raw email to {recipient_email}: {e}")
            return False
