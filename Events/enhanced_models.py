from django.db import models
from Authentication.models import CustomUser
from Events.models import Event, EventTicket, EventFeedback
from datetime import datetime
import uuid
import secrets


class EventRoom(models.Model):
    """Dedicated room for event discussions and materials"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='event_room')
    room = models.ForeignKey('Rooms.Room', on_delete=models.CASCADE, related_name='associated_event')
    
    # Activation
    is_active = models.BooleanField(default=False)
    activated_at = models.DateTimeField(null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    activated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='activated_event_rooms')
    
    # Expiry
    auto_expire = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    grace_period_hours = models.IntegerField(default=24)  # After event ends
    
    # Access Control
    requires_ticket = models.BooleanField(default=False)
    allowed_before_event_hours = models.IntegerField(default=24)
    
    # Chat Features
    enable_chat = models.BooleanField(default=True)
    enable_file_sharing = models.BooleanField(default=True)
    enable_voice_chat = models.BooleanField(default=False)
    enable_video_chat = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['event', 'is_active']),
        ]
    
    def __str__(self):
        return f"Room for {self.event.name}"


class EventResourceAccess(models.Model):
    """Payment-gated access to event resources"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='resource_access_controls')
    resource = models.ForeignKey('Resources.Resource', on_delete=models.CASCADE)
    
    # Access Control
    access_type = models.CharField(max_length=50, choices=(
        ('free', 'Free Access'),
        ('ticket_only', 'Ticket Holder Only'),
        ('paid', 'Paid Access'),
        ('sponsor_only', 'Sponsor Only'),
        ('speaker_only', 'Speaker Only'),
        ('organizer_only', 'Organizer Only'),
    ), default='ticket_only')
    
    # Payment
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_required = models.BooleanField(default=False)
    
    # Visibility Timeline
    visible_before_event = models.BooleanField(default=False)
    visible_during_event = models.BooleanField(default=True)
    visible_after_event = models.BooleanField(default=True)
    days_visible_before = models.IntegerField(default=0)
    days_visible_after = models.IntegerField(default=30)
    
    # Tracking
    view_count = models.IntegerField(default=0)
    download_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(default=datetime.now)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['event', 'access_type']),
        ]
    
    def __str__(self):
        return f"Access: {self.resource} for {self.event.name}"


class EventResourcePurchase(models.Model):
    """Track resource purchases"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='event_resource_purchases')
    resource_access = models.ForeignKey(EventResourceAccess, on_delete=models.CASCADE, related_name='purchases')
    
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_option = models.CharField(max_length=100)
    transaction = models.ForeignKey('Payment.TransactionToken', on_delete=models.SET_NULL, null=True, blank=True)
    
    purchased_at = models.DateTimeField(default=datetime.now)
    access_expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'resource_access']
        indexes = [
            models.Index(fields=['user', 'purchased_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} purchased {self.resource_access.resource}"


class EventInterest(models.Model):
    """Mark as interested in event"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='interests')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='interested_events')
    
    interested = models.BooleanField(default=True)
    notify_updates = models.BooleanField(default=True)
    marked_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        unique_together = ['event', 'user']
        indexes = [
            models.Index(fields=['user', 'interested']),
        ]
    
    def __str__(self):
        return f"{self.user.email} interested in {self.event.name}"


class EventReaction(models.Model):
    """Enhanced reaction system"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='event_reactions')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='event_reactions_given')
    
    reaction_type = models.CharField(max_length=50, choices=(
        ('like', 'Like'),
        ('love', 'Love'),
        ('excited', 'Excited'),
        ('interested', 'Interested'),
        ('attending', 'Definitely Attending'),
        ('maybe', 'Maybe Attending'),
    ))
    
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        unique_together = ['event', 'user']
        indexes = [
            models.Index(fields=['event', 'reaction_type']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.reaction_type} - {self.event.name}"


class EventComment(models.Model):
    """Comments on events"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='event_comments')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='event_comments_made')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    
    content = models.TextField(max_length=2000)
    is_visible = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['event', '-created_at']),
            models.Index(fields=['user']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment by {self.user.email} on {self.event.name}"


class EventPin(models.Model):
    """Pin events to dashboard"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='pins')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='pinned_events')
    pinned_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        unique_together = ['event', 'user']
    
    def __str__(self):
        return f"{self.user.email} pinned {self.event.name}"


class EventRepost(models.Model):
    """Repost events"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='event_reposts')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='event_reposts_made')
    reposted_to = models.ManyToManyField('Rooms.Room', blank=True, related_name='reposted_events')
    
    caption = models.TextField(max_length=500, blank=True)
    reposted_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', '-reposted_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} reposted {self.event.name}"


class EventShare(models.Model):
    """Track event shares"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='event_shares')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='events_shared')
    
    share_type = models.CharField(max_length=50, choices=(
        ('internal', 'Shared within Platform'),
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter/X'),
        ('linkedin', 'LinkedIn'),
        ('whatsapp', 'WhatsApp'),
        ('telegram', 'Telegram'),
        ('email', 'Email'),
        ('link', 'Copy Link'),
        ('instagram', 'Instagram'),
    ))
    
    shared_to = models.JSONField(default=dict, blank=True)  # {room_ids: [], user_ids: []}
    shared_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['event', 'share_type']),
        ]
    
    def __str__(self):
        return f"{self.user.email} shared {self.event.name} via {self.share_type}"


class EventSocialLink(models.Model):
    """Generate shareable links"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='social_links')
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    
    token = models.CharField(max_length=255, unique=True, db_index=True)
    platform = models.CharField(max_length=50, blank=True)
    clicks = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(default=datetime.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Share link for {self.event.name}"
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)


class EventBlock(models.Model):
    """Block events from feed"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='blocks')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='blocked_events')
    reason = models.TextField(max_length=500, blank=True)
    blocked_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        unique_together = ['event', 'user']
    
    def __str__(self):
        return f"{self.user.email} blocked {self.event.name}"


class EventUserReport(models.Model):
    """User reports on events"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='user_event_reports')
    reporter = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reported_events_list')
    
    report_type = models.CharField(max_length=50, choices=(
        ('spam', 'Spam'),
        ('inappropriate', 'Inappropriate Content'),
        ('misleading', 'Misleading Information'),
        ('scam', 'Potential Scam'),
        ('duplicate', 'Duplicate Event'),
        ('cancelled_not_updated', 'Event Cancelled but Not Updated'),
        ('fake_event', 'Fake Event'),
        ('other', 'Other'),
    ))
    
    description = models.TextField(max_length=1000)
    status = models.CharField(max_length=50, choices=(
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
        ('action_taken', 'Action Taken'),
    ), default='pending')
    
    reported_at = models.DateTimeField(default=datetime.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_event_reports_list')
    admin_notes = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', '-reported_at']),
        ]
    
    def __str__(self):
        return f"Report on {self.event.name} by {self.reporter.email}"


class EventTicketPurchase(models.Model):
    """Link tickets to payment system"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(EventTicket, on_delete=models.CASCADE, related_name='ticket_purchases')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='purchased_event_tickets')
    
    quantity = models.IntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment Integration
    payment_option = models.CharField(max_length=100)
    transaction = models.ForeignKey('Payment.TransactionToken', on_delete=models.SET_NULL, null=True, blank=True)
    payment_status = models.CharField(max_length=50, choices=(
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ), default='pending')
    
    # Ticket Details
    ticket_codes = models.JSONField(default=list)  # List of QR codes/unique identifiers
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    # Transfer
    is_transferable = models.BooleanField(default=True)
    transferred_to = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_tickets')
    transferred_at = models.DateTimeField(null=True, blank=True)
    
    purchased_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'ticket']),
            models.Index(fields=['payment_status']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.ticket.event.name} ({self.quantity}x)"


class EventBrowserReminder(models.Model):
    """Browser push notifications"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='browser_reminders')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='event_browser_reminders')
    
    remind_at = models.DateTimeField()
    remind_before_minutes = models.IntegerField()  # 15, 30, 60, 1440 (1 day), etc.
    
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Browser notification subscription
    subscription_info = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['remind_at', 'sent']),
        ]
    
    def __str__(self):
        return f"Reminder for {self.user.email} - {self.event.name}"


class EventEmailReminder(models.Model):
    """Email reminders"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='email_reminders')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='event_email_reminders')
    
    remind_at = models.DateTimeField()
    remind_before_hours = models.IntegerField()  # 1, 24, 48, 72, etc.
    
    email_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['remind_at', 'email_sent']),
        ]
    
    def __str__(self):
        return f"Email reminder for {self.user.email} - {self.event.name}"


class EventToAnnouncementConversion(models.Model):
    """Track event to announcement conversions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='announcement_conversions')
    announcement = models.ForeignKey('Announcements.Announcements', on_delete=models.CASCADE)
    converted_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    
    retain_event = models.BooleanField(default=True)  # Keep original event
    converted_at = models.DateTimeField(default=datetime.now)
    
    def __str__(self):
        return f"Converted {self.event.name} to announcement"


class EventHelpRequest(models.Model):
    """Users can request help from organizers"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='help_support_requests')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='event_help_support_requests')
    
    subject = models.CharField(max_length=200)
    message = models.TextField(max_length=2000)
    
    status = models.CharField(max_length=50, choices=(
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ), default='pending')
    
    priority = models.CharField(max_length=20, choices=(
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ), default='medium')
    
    created_at = models.DateTimeField(default=datetime.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['event', 'status']),
        ]
    
    def __str__(self):
        return f"Help request for {self.event.name} by {self.user.email}"


class EventHelpResponse(models.Model):
    """Organizer responses to help requests"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(EventHelpRequest, on_delete=models.CASCADE, related_name='help_responses')
    responder = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='given_event_help_responses')
    
    message = models.TextField(max_length=2000)
    is_solution = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    def __str__(self):
        return f"Response to help request by {self.responder.email}"


class EventPermission(models.Model):
    """Granular event permissions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='event_permissions')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='event_permissions_granted')
    
    # CRUD
    can_view = models.BooleanField(default=True)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    
    # Management
    can_manage_tickets = models.BooleanField(default=False)
    can_manage_resources = models.BooleanField(default=False)
    can_manage_logistics = models.BooleanField(default=False)
    can_invite_users = models.BooleanField(default=False)
    can_approve_registrations = models.BooleanField(default=False)
    can_moderate_feedback = models.BooleanField(default=False)
    can_manage_sponsors = models.BooleanField(default=False)
    
    # Room
    can_manage_room = models.BooleanField(default=False)
    
    # Content
    can_post_announcements = models.BooleanField(default=False)
    can_respond_to_help = models.BooleanField(default=False)
    
    granted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='granted_event_perms')
    granted_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        unique_together = ['event', 'user']
        indexes = [
            models.Index(fields=['event', 'user']),
        ]
    
    def __str__(self):
        return f"Permissions for {self.user.email} on {self.event.name}"
