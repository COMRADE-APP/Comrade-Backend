"""
Enhanced serializers for Events system
Includes ticketing, resources, sharing, reactions, and permissions
"""
from rest_framework import serializers
from Events.models import Event, EventTicket, EventFeedback
from Events.enhanced_models import (
    EventRoom, EventResourceAccess, EventResourcePurchase,
    EventInterest, EventReaction, EventComment, EventPin,
    EventRepost, EventShare, EventSocialLink, EventBlock,
    EventUserReport, EventTicketPurchase, EventBrowserReminder,
    EventEmailReminder, EventToAnnouncementConversion,
    EventHelpRequest, EventHelpResponse, EventPermission
)
from Authentication.models import CustomUser


class EventRoomSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.name', read_only=True)
    room_name = serializers.CharField(source='room.name', read_only=True)
    
    class Meta:
        model = EventRoom
        fields = [
            'id', 'event', 'event_name', 'room', 'room_name',
            'is_active', 'activated_at', 'deactivated_at',
            'auto_expire', 'expires_at', 'grace_period_hours',
            'requires_ticket', 'allowed_before_event_hours',
            'enable_chat', 'enable_file_sharing', 'enable_voice_chat',
            'enable_video_chat', 'created_at'
        ]
        read_only_fields = ['id', 'activated_at', 'deactivated_at', 'created_at']


class EventResourceAccessSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.name', read_only=True)
    
    class Meta:
        model = EventResourceAccess
        fields = [
            'id', 'event', 'event_name', 'resource', 'access_type',
            'price', 'payment_required', 'visible_before_event',
            'visible_during_event', 'visible_after_event',
            'days_visible_before', 'days_visible_after',
            'view_count', 'download_count', 'created_at'
        ]
        read_only_fields = ['id', 'view_count', 'download_count', 'created_at']


class EventResourcePurchaseSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = EventResourcePurchase
        fields = [
            'id', 'user', 'user_email', 'resource_access',
            'amount_paid', 'payment_option', 'transaction',
            'purchased_at', 'access_expires_at'
        ]
        read_only_fields = ['id', 'purchased_at']


class EventInterestSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = EventInterest
        fields = ['id', 'event', 'user', 'user_email', 'interested', 'notify_updates', 'marked_at']
        read_only_fields = ['id', 'marked_at']


class EventReactionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = EventReaction
        fields = ['id', 'event', 'user', 'user_email', 'reaction_type', 'created_at']
        read_only_fields = ['id', 'created_at']


class EventCommentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = EventComment
        fields = [
            'id', 'event', 'user', 'user_email', 'user_name', 'parent',
            'content', 'is_visible', 'is_pinned', 'is_edited',
            'created_at', 'updated_at', 'replies'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
    
    def get_replies(self, obj):
        if obj.replies.exists():
            return EventCommentSerializer(obj.replies.all(), many=True).data
        return []


class EventPinSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.name', read_only=True)
    
    class Meta:
        model = EventPin
        fields = ['id', 'event', 'event_name', 'user', 'pinned_at']
        read_only_fields = ['id', 'pinned_at']


class EventRepostSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    reposted_to_names = serializers.SerializerMethodField()
    
    class Meta:
        model = EventRepost
        fields = [
            'id', 'event', 'event_name', 'user', 'user_email',
            'reposted_to', 'reposted_to_names', 'caption', 'reposted_at'
        ]
        read_only_fields = ['id', 'reposted_at']
    
    def get_reposted_to_names(self, obj):
        return [room.name for room in obj.reposted_to.all()]


class EventShareSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = EventShare
        fields = [
            'id', 'event', 'event_name', 'user', 'user_email',
            'share_type', 'shared_to', 'shared_at'
        ]
        read_only_fields = ['id', 'shared_at']


class EventSocialLinkSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.name', read_only=True)
    
    class Meta:
        model = EventSocialLink
        fields = [
            'id', 'event', 'event_name', 'created_by', 'token',
            'platform', 'clicks', 'created_at', 'expires_at'
        ]
        read_only_fields = ['id', 'token', 'clicks', 'created_at']


class EventBlockSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.name', read_only=True)
    
    class Meta:
        model = EventBlock
        fields = ['id', 'event', 'event_name', 'user', 'reason', 'blocked_at']
        read_only_fields = ['id', 'blocked_at']


class EventUserReportSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.name', read_only=True)
    reporter_email = serializers.EmailField(source='reporter.email', read_only=True)
    
    class Meta:
        model = EventUserReport
        fields = [
            'id', 'event', 'event_name', 'reporter', 'reporter_email',
            'report_type', 'description', 'status',
            'reported_at', 'reviewed_at', 'reviewed_by', 'admin_notes'
        ]
        read_only_fields = ['id', 'reported_at', 'reviewed_at', 'reviewed_by']


class EventTicketPurchaseSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    event_name = serializers.CharField(source='ticket.event.name', read_only=True)
    ticket_type = serializers.CharField(source='ticket.ticket_type', read_only=True)
    
    class Meta:
        model = EventTicketPurchase
        fields = [
            'id', 'ticket', 'ticket_type', 'event_name', 'user', 'user_email',
            'quantity', 'total_price', 'payment_option', 'transaction',
            'payment_status', 'ticket_codes', 'is_used', 'used_at',
            'is_transferable', 'transferred_to', 'transferred_at', 'purchased_at'
        ]
        read_only_fields = ['id', 'purchased_at', 'ticket_codes']


class EventBrowserReminderSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.name', read_only=True)
    
    class Meta:
        model = EventBrowserReminder
        fields = [
            'id', 'event', 'event_name', 'user', 'remind_at',
            'remind_before_minutes', 'sent', 'sent_at',
            'subscription_info', 'created_at'
        ]
        read_only_fields = ['id', 'sent', 'sent_at', 'created_at']


class EventEmailReminderSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.name', read_only=True)
    
    class Meta:
        model = EventEmailReminder
        fields = [
            'id', 'event', 'event_name', 'user', 'remind_at',
            'remind_before_hours', 'email_sent', 'sent_at', 'created_at'
        ]
        read_only_fields = ['id', 'email_sent', 'sent_at', 'created_at']


class EventConversionSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.name', read_only=True)
    
    class Meta:
        model = EventToAnnouncementConversion
        fields = [
            'id', 'event', 'event_name', 'announcement',
            'converted_by', 'retain_event', 'converted_at'
        ]
        read_only_fields = ['id', 'converted_at']


class EventHelpRequestSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    responses = serializers.SerializerMethodField()
    
    class Meta:
        model = EventHelpRequest
        fields = [
            'id', 'event', 'event_name', 'user', 'user_email',
            'subject', 'message', 'status', 'priority',
            'created_at', 'resolved_at', 'responses'
        ]
        read_only_fields = ['id', 'created_at', 'resolved_at']
    
    def get_responses(self, obj):
        return EventHelpResponseSerializer(obj.help_responses.all(), many=True).data


class EventHelpResponseSerializer(serializers.ModelSerializer):
    responder_email = serializers.EmailField(source='responder.email', read_only=True)
    responder_name = serializers.SerializerMethodField()
    
    class Meta:
        model = EventHelpResponse
        fields = [
            'id', 'request', 'responder', 'responder_email', 'responder_name',
            'message', 'is_solution', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_responder_name(self, obj):
        return f"{obj.responder.first_name} {obj.responder.last_name}".strip() or obj.responder.email


class EventPermissionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)
    
    class Meta:
        model = EventPermission
        fields = [
            'id', 'event', 'event_name', 'user', 'user_email',
            'can_view', 'can_edit', 'can_delete',
            'can_manage_tickets', 'can_manage_resources', 'can_manage_logistics',
            'can_invite_users', 'can_approve_registrations', 'can_moderate_feedback',
            'can_manage_sponsors', 'can_manage_room',
            'can_post_announcements', 'can_respond_to_help',
            'granted_by', 'granted_at'
        ]
        read_only_fields = ['id', 'granted_at']


# Enhanced Event Serializer
class EventDetailSerializer(serializers.ModelSerializer):
    """Comprehensive event serializer with all related data"""
    created_by_name = serializers.SerializerMethodField()
    room = EventRoomSerializer(source='event_room', read_only=True)
    reactions_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    interested_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'name', 'description', 'capacity', 'duration',
            'start_time', 'end_time', 'booking_deadline', 'booking_status',
            'attendees', 'attendees_viewable', 'activate_feedback',
            'event_date', 'deadline_reached', 'location', 'status',
            'scheduled_time', 'time_stamp', 'created_by', 'created_by_name',
            'room', 'reactions_count', 'comments_count', 'interested_count'
        ]
        read_only_fields = ['id', 'time_stamp']
    
    def get_created_by_name(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email
    
    def get_reactions_count(self, obj):
        return obj.event_reactions.count()
    
    def get_comments_count(self, obj):
        return obj.event_comments.filter(parent__isnull=True).count()
    
    def get_interested_count(self, obj):
        return obj.interests.filter(interested=True).count()
