"""
Django signals for Events app
Auto-creates rooms when events are created and handles room expiry
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

from Events.models import Event
from Events.enhanced_models import EventRoom


@receiver(post_save, sender=Event)
def create_event_room(sender, instance, created, **kwargs):
    """
    Auto-create a Room and EventRoom when a new Event is created.
    The room will be set to expire after the event ends + grace period.
    """
    if created:
        # Import Room here to avoid circular imports
        from Rooms.models import Room
        
        # Create the room for this event
        room = Room.objects.create(
            name=f"Event: {instance.name}",
            description=f"Discussion room for the event: {instance.name}",
            avatar=None,
            cover_image=None,
            created_by=instance.created_by,
        )
        
        # Calculate room expiry based on event end date
        grace_period_hours = 24  # Default grace period
        if instance.complexity_level == 'sophisticated':
            grace_period_hours = 72  # Longer for complex events
        elif instance.complexity_level == 'midlevel':
            grace_period_hours = 48
        
        # Event date + duration + grace period
        expires_at = None
        if instance.event_date:
            if instance.duration:
                expires_at = instance.event_date + instance.duration + timedelta(hours=grace_period_hours)
            else:
                expires_at = instance.event_date + timedelta(hours=grace_period_hours)
        
        # Create EventRoom linking
        EventRoom.objects.create(
            event=instance,
            room=room,
            is_active=False,  # Inactive until event starts
            auto_expire=True,
            expires_at=expires_at,
            grace_period_hours=grace_period_hours,
            requires_ticket=instance.booking_status != 'open',
            allowed_before_event_hours=24,
            enable_chat=True,
            enable_file_sharing=True,
        )


@receiver(post_save, sender=Event)
def update_event_room_on_status_change(sender, instance, created, **kwargs):
    """
    Update room status when event status changes
    """
    if not created:
        try:
            event_room = instance.event_room
            
            # Activate room when event becomes active/live
            if instance.status in ['active', 'live', 'ongoing']:
                if not event_room.is_active:
                    event_room.is_active = True
                    event_room.activated_at = timezone.now()
                    event_room.save()
            
            # Deactivate room when event ends/cancels
            elif instance.status in ['completed', 'cancelled', 'archived']:
                if event_room.is_active:
                    event_room.is_active = False
                    event_room.deactivated_at = timezone.now()
                    event_room.save()
                    
        except EventRoom.DoesNotExist:
            pass  # No room linked to this event
