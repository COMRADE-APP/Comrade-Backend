"""
Institution Signals
Auto-create rooms for institutions and organizations when they are created
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid

from Institution.models import Institution, Organization


@receiver(post_save, sender=Institution)
def create_institution_room(sender, instance, created, **kwargs):
    """
    Auto-create a room for the institution when it's created
    """
    if created:
        try:
            from Rooms.models import Room, RoomSettings
            
            # Create a room for the institution
            room = Room.objects.create(
                name=f"{instance.name} - Community",
                description=f"Official discussion room for {instance.name}",
                room_code=uuid.uuid4().hex[:10].upper(),
                created_by=instance.created_by,
                operation_state='active',
            )
            
            # Add institution to the room's ManyToManyField
            room.institutions.add(instance)
            
            # Add creator as admin if available
            if instance.created_by:
                room.admins.add(instance.created_by)
                room.members.add(instance.created_by)
            
            # Create room settings
            RoomSettings.objects.create(
                room=room,
                chat_enabled=True,
                require_approval_to_join=False,
                is_discoverable=True,
            )
            
            print(f"✓ Created room '{room.name}' for institution '{instance.name}'")
            
        except Exception as e:
            print(f"✗ Failed to create room for institution '{instance.name}': {e}")


@receiver(post_save, sender=Organization)
def create_organization_room(sender, instance, created, **kwargs):
    """
    Auto-create a room for the organization when it's created
    """
    if created:
        try:
            from Rooms.models import Room, RoomSettings
            
            # Create a room for the organization
            room = Room.objects.create(
                name=f"{instance.name} - Community",
                description=f"Official discussion room for {instance.name}",
                room_code=uuid.uuid4().hex[:10].upper(),
                created_by=instance.created_by,
                operation_state='active',
            )
            
            # Add organization to the room's ManyToManyField
            room.organisation.add(instance)
            
            # Add creator as admin if available
            if instance.created_by:
                room.admins.add(instance.created_by)
                room.members.add(instance.created_by)
            
            # Create room settings
            RoomSettings.objects.create(
                room=room,
                chat_enabled=True,
                require_approval_to_join=False,
                is_discoverable=True,
            )
            
            print(f"✓ Created room '{room.name}' for organization '{instance.name}'")
            
        except Exception as e:
            print(f"✗ Failed to create room for organization '{instance.name}': {e}")

