"""
Auto-creation utilities for default rooms when entities are created
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from Institution.models import Institution
from Organisation.models import Organisation
from Specialization.models import Specialization
from Rooms.models import Room, DefaultRoom
from datetime import datetime
import secrets


def generate_room_code():
    """Generate unique room code"""
    return secrets.token_hex(5).upper()


@receiver(post_save, sender=Institution)
def create_institution_default_rooms(sender, instance, created, **kwargs):
    """Auto-create default rooms when an Institution is created"""
    if created and instance.created_by:
        # Main institutional rooms
        base_rooms = [
            {
                'name': f'{instance.name} - General Hub',
                'description': 'General discussion and announcements for all institution members',
                'text_priority': 'all_members',
                'operation_state': 'active',
            },
            {
                'name': f'{instance.name} - Announcements',
                'description': 'Official institutional announcements',
                'text_priority': 'admins_only',
                'operation_state': 'active',
            },
            {
                'name': f'{instance.name} - Resources',
                'description': 'Shared institutional resources and documents',
                'text_priority': 'all_members',
                'operation_state': 'active',
            },
            {
                'name': f'{instance.name} - Staff',
                'description': 'Staff-only discussions',
                'text_priority': 'admins_moderators_only',
                'operation_state': 'active',
            },
            {
                'name': f'{instance.name} - Events',
                'description': 'Institutional events and activities',
                'text_priority': 'all_members',
                'operation_state': 'active',
            },
        ]
        
        created_rooms = []
        for room_data in base_rooms:
            room = Room.objects.create(
                created_by=instance.created_by,
                **room_data
            )
            # Add created_by as admin
            room.admins.add(instance.created_by)
            room.members.add(instance.created_by)
            # Link to institution
            room.institutions.add(instance)
            created_rooms.append(room)
        
        # Create default room container
        default_room = DefaultRoom.objects.create(
            name=f"{instance.name} - Default Rooms",
            inst_or_org_name=instance.name,
            reference_object_code=str(instance.id),
            created_by=instance.created_by,
            operation_state='active'
        )
        default_room.rooms.set(created_rooms)
        default_room.admins.add(instance.created_by)
        default_room.members.add(instance.created_by)
        
        print(f"Created {len(created_rooms)} default rooms for Institution: {instance.name}")
        return created_rooms


@receiver(post_save, sender=Organisation)
def create_organization_default_rooms(sender, instance, created, **kwargs):
    """Auto-create default rooms when an Organization is created"""
    if created and instance.created_by:
        base_rooms = [
            {
                'name': f'{instance.name} - Hub',
                'description': 'Main organization hub for all members',
                'text_priority': 'all_members',
                'operation_state': 'active',
            },
            {
                'name': f'{instance.name} - Projects',
                'description': 'Organization projects and initiatives',
                'text_priority': 'all_members',
                'operation_state': 'active',
            },
            {
                'name': f'{instance.name} - Team',
                'description': 'Internal team discussions',
                'text_priority': 'admins_moderators_only',
                'operation_state': 'active',
            },
            {
                'name': f'{instance.name} - Resources',
                'description': 'Organization resources and documents',
                'text_priority': 'all_members',
                'operation_state': 'active',
            },
        ]
        
        created_rooms = []
        for room_data in base_rooms:
            room = Room.objects.create(
                created_by=instance.created_by,
                **room_data
            )
            room.admins.add(instance.created_by)
            room.members.add(instance.created_by)
            print(instance)
            room.organisation.add(instance)
            created_rooms.append(room)
        
        # Create default room container
        default_room = DefaultRoom.objects.create(
            name=f"{instance.name} - Default Rooms",
            inst_or_org_name=instance.name,
            reference_object_code=str(instance.id),
            created_by=instance.created_by,
            operation_state='active'
        )
        default_room.rooms.set(created_rooms)
        default_room.admins.add(instance.created_by)
        default_room.members.add(instance.created_by)
        
        print(f"Created {len(created_rooms)} default rooms for Organization: {instance.name}")
        return created_rooms


def create_specialization_room_optional(specialization, create_room=True):
    """
    Optionally create a room for a Specialization
    This is called manually or via a signal based on creator preference
    """
    if not create_room or not specialization.created_by:
        return None
    
    room = Room.objects.create(
        name=f'{specialization.name} - Community',
        description=f'Community discussion for {specialization.name} specialization',
        created_by=specialization.created_by,
        text_priority='all_members',
        operation_state='active'
    )
    
    room.admins.add(specialization.created_by)
    room.members.add(specialization.created_by)
    
    print(f"Created room for Specialization: {specialization.name}")
    return room


def create_faculty_rooms(institution, faculty_data):
    """
    Create rooms for faculties/departments within an institution
    faculty_data: list of dicts with 'name' and optional 'description'
    """
    created_rooms = []
    
    for faculty in faculty_data:
        room = Room.objects.create(
            name=f"{institution.name} - {faculty['name']}",
            description=faculty.get('description', f"{faculty['name']} discussions"),
            created_by=institution.created_by,
            text_priority='all_members',
            operation_state='active'
        )
        room.institutions.add(institution)
        room.admins.add(institution.created_by)
        
        # Student-specific sub-room
        student_room = Room.objects.create(
            name=f"{institution.name} - {faculty['name']} Students",
            description=f"Student discussions for {faculty['name']}",
            created_by=institution.created_by,
            text_priority='all_members',
            operation_state='active'
        )
        student_room.institutions.add(institution)
        student_room.admins.add(institution.created_by)
        
        created_rooms.extend([room, student_room])
    
    return created_rooms


def add_user_to_entity_rooms(user, entity_type, entity_id):
    """
    Add user to all relevant rooms when they join an institution/organization
    entity_type: 'institution' or 'organization'
    entity_id: UUID of the entity
    """
    if entity_type == 'institution':
        rooms = Room.objects.filter(institutions__id=entity_id)
    elif entity_type == 'organization':
        rooms = Room.objects.filter(organisation__id=entity_id)
    else:
        return []
    
    added_to = []
    for room in rooms:
        # Only add to general/public rooms, not staff-only rooms
        if room.operation_state == 'active' and room.text_priority in ['all_members', 'admins_moderators_only']:
            room.members.add(user)
            added_to.append(room)
    
    return added_to
