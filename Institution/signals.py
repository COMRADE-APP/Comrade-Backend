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
            
            print(f"[SUCCESS] Created room '{room.name}' for institution '{instance.name}'")
            
        except Exception as e:
            print(f"[ERROR] Failed to create room for institution '{instance.name}': {e}")



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
            
            print(f"[SUCCESS] Created room '{room.name}' for organization '{instance.name}'")
            
        except Exception as e:
            print(f"[ERROR] Failed to create room for organization '{instance.name}': {e}")



from Institution.models import (
    InstBranch, InstDepartment, Programme,
    VCOffice, Faculty, AdminDep, RegistrarOffice, HR, ICT, Finance, Marketing, Legal,
    StudentAffairs, Admissions, CareerOffice, Counselling,
    SupportServices, Security, Transport, Library, Cafeteria, Hostel, HealthServices,
    OtherInstitutionUnit
)

@receiver(post_save, sender=InstBranch)
@receiver(post_save, sender=InstDepartment)
@receiver(post_save, sender=Programme)
@receiver(post_save, sender=VCOffice)
@receiver(post_save, sender=Faculty)
@receiver(post_save, sender=AdminDep)
@receiver(post_save, sender=RegistrarOffice)
@receiver(post_save, sender=HR)
@receiver(post_save, sender=ICT)
@receiver(post_save, sender=Finance)
@receiver(post_save, sender=Marketing)
@receiver(post_save, sender=Legal)
@receiver(post_save, sender=StudentAffairs)
@receiver(post_save, sender=Admissions)
@receiver(post_save, sender=CareerOffice)
@receiver(post_save, sender=Counselling)
@receiver(post_save, sender=SupportServices)
@receiver(post_save, sender=Security)
@receiver(post_save, sender=Transport)
@receiver(post_save, sender=Library)
@receiver(post_save, sender=Cafeteria)
@receiver(post_save, sender=Hostel)
@receiver(post_save, sender=HealthServices)
@receiver(post_save, sender=OtherInstitutionUnit)
def auto_create_unit_room(sender, instance, created, **kwargs):
    """
    Auto-create a room when any Institution Unit is created
    """
    if created:
        try:
            from Rooms.models import Room, RoomSettings
            
            # Determine Institution Context
            institution = None
            if hasattr(instance, 'institution') and instance.institution:
                institution = instance.institution
            elif hasattr(instance, 'department') and instance.department:
                 if instance.department.institution:
                     institution = instance.department.institution
                 elif instance.department.faculty and instance.department.faculty.institution:
                     institution = instance.department.faculty.institution
            
            context_name = institution.name if institution else "Institution"
            
            # Construct Room Name
            unit_type_name = sender._meta.verbose_name
            room_name = f"{context_name} - {instance.name} {unit_type_name}"
            
            # Ensure name fits in 255 chars
            if len(room_name) > 255:
                room_name = room_name[:252] + "..."
            
            description = f"Official discussion room for {instance.name} ({unit_type_name})"
            
            # Create the room
            room = Room.objects.create(
                name=room_name,
                description=description,
                room_code=uuid.uuid4().hex[:10].upper(),
                created_by=instance.created_by,
                operation_state='active',
            )
            
            # Link to institution
            if institution:
                room.institutions.add(institution)
            
            # Add creator as admin
            if instance.created_by:
                room.admins.add(instance.created_by)
                room.members.add(instance.created_by)
            
            # Create room settings
            RoomSettings.objects.create(
                room=room,
                chat_enabled=True,
                is_discoverable=True,
            )
            
            print(f"[SUCCESS] Created room '{room.name}' for {unit_type_name} '{instance.name}'")
            
        except Exception as e:
            print(f"[ERROR] Failed to create room for {sender.__name__} '{instance.name}': {e}")



