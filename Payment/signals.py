"""
Auto-Kitty Signals
Automatically creates a PaymentGroups 'kitty' when key entities are created.
This lets every Business, CapitalVenture, ShopRegistration, Organisation,
Institution, and Specialization have its own fund pool for tracking money.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)


def _create_kitty_for_entity(instance, entity_name, owner_user, target_amount=None):
    """
    Shared helper that creates a PaymentGroups kitty for the given entity.
    `owner_user` must be the CustomUser (auth user), not Profile.
    """
    from Payment.models import PaymentGroups, PaymentProfile

    ct = ContentType.objects.get_for_model(instance)
    obj_id = str(instance.pk)

    # Don't create duplicate kitties
    if PaymentGroups.objects.filter(
        entity_content_type=ct, entity_object_id=obj_id, group_type='kitty'
    ).exists():
        return

    # Resolve the creator's PaymentProfile (get_or_create)
    profile = None
    if owner_user:
        try:
            from Authentication.models import Profile as AuthProfile
            auth_profile = AuthProfile.objects.filter(user=owner_user).first()
            if auth_profile:
                profile, _ = PaymentProfile.objects.get_or_create(user=auth_profile)
        except Exception as e:
            logger.warning(f"Could not resolve PaymentProfile for {owner_user}: {e}")

    kitty = PaymentGroups.objects.create(
        name=f"{entity_name} Fund Pool",
        description=f"Auto-created kitty for {entity_name}",
        creator=profile,
        group_type='kitty',
        entity_content_type=ct,
        entity_object_id=obj_id,
        target_amount=target_amount,
        contribution_type='flexible',
        frequency='one_time',
        is_public=False,
        requires_approval=False,
    )
    logger.info(f"Created kitty '{kitty.name}' (id={kitty.pk}) for {ct.model} #{obj_id}")


# ──────────────────────────────────────────────
# 1. Funding: Business
# ──────────────────────────────────────────────
@receiver(post_save, sender='Funding.Business')
def create_business_kitty(sender, instance, created, **kwargs):
    if not created:
        return
    target = getattr(instance, 'charity_goal', None)
    _create_kitty_for_entity(instance, instance.name, instance.founder, target_amount=target)


# ──────────────────────────────────────────────
# 2. Funding: CapitalVenture
# ──────────────────────────────────────────────
@receiver(post_save, sender='Funding.CapitalVenture')
def create_venture_kitty(sender, instance, created, **kwargs):
    if not created:
        return
    target = getattr(instance, 'total_fund', None)
    _create_kitty_for_entity(instance, instance.name, instance.created_by, target_amount=target)


# ──────────────────────────────────────────────
# 3. Payment: ShopRegistration
# ──────────────────────────────────────────────
@receiver(post_save, sender='Payment.ShopRegistration')
def create_shop_kitty(sender, instance, created, **kwargs):
    if not created:
        return
    # ShopRegistration.owner is a Profile, get the underlying user
    owner_user = instance.owner.user if instance.owner else None
    _create_kitty_for_entity(instance, instance.name, owner_user)


# ──────────────────────────────────────────────
# 4. Organisation: Organisation
# ──────────────────────────────────────────────
@receiver(post_save, sender='Organisation.Organisation')
def create_organisation_kitty(sender, instance, created, **kwargs):
    if not created:
        return
    _create_kitty_for_entity(instance, instance.name, instance.created_by)


# ──────────────────────────────────────────────
# 5. Institution: Institution
# ──────────────────────────────────────────────
@receiver(post_save, sender='Institution.Institution')
def create_institution_kitty(sender, instance, created, **kwargs):
    if not created:
        return
    _create_kitty_for_entity(instance, instance.name, instance.created_by)


# ──────────────────────────────────────────────
# 6. Specialization: Specialization
# ──────────────────────────────────────────────
@receiver(post_save, sender='Specialization.Specialization')
def create_specialization_kitty(sender, instance, created, **kwargs):
    if not created:
        return
    # created_by is M2M, so grab the first creator if available
    owner_user = None
    try:
        first_creator = instance.created_by.first()
        if first_creator:
            owner_user = first_creator.user  # Profile → CustomUser
    except Exception:
        pass
    target = instance.price if getattr(instance, 'is_paid', False) else None
    _create_kitty_for_entity(
        instance,
        f"{instance.name} ({instance.get_learning_type_display()})",
        owner_user,
        target_amount=target,
    )


# ──────────────────────────────────────────────
# 7. Auto-create Room when PaymentGroup is created
# ──────────────────────────────────────────────
@receiver(post_save, sender='Payment.PaymentGroups')
def auto_create_room_for_group(sender, instance, created, **kwargs):
    """Auto-create a linked Room when a PaymentGroup is created (if auto_create_room=True)."""
    if not created:
        return
    if not instance.auto_create_room or instance.linked_room:
        return
    # Skip kitties – they don't need rooms
    if instance.group_type == 'kitty':
        return
    try:
        from Rooms.models import Room

        # Resolve the creator's CustomUser
        creator_user = None
        if instance.creator and instance.creator.user:
            creator_user = instance.creator.user.user  # PaymentProfile -> Profile -> CustomUser

        room = Room(
            name=instance.name,
            description=instance.description or f"Room for {instance.name} group",
            created_by=creator_user,
        )
        room.save()

        # Add creator as admin and member
        if creator_user:
            room.admins.add(creator_user)
            room.members.add(creator_user)

        # Link room to group (use update to avoid re-triggering signal)
        from Payment.models import PaymentGroups as PG
        PG.objects.filter(pk=instance.pk).update(linked_room=room)
        instance.refresh_from_db()
        logger.info(f"Auto-created room '{room.name}' for group '{instance.name}'")
    except Exception as e:
        logger.warning(f"Failed to auto-create room for group {instance.name}: {e}")

