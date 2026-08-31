"""Shared permission classes for Events-related write protection.

Phase 0 lockdown: secondary Event* viewsets previously used
IsAuthenticatedOrReadOnly over an unscoped queryset, letting any authenticated
user modify any other user's event resources. These classes keep public reads
but restrict unsafe methods to the related event's creator, its organizer,
platform staff, or the record's own owner.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Event

# Models a normal member may manage for themselves
OWNER_FIELDS = (
    "user", "attendee", "member", "created_by", "proposer",
    "follower", "added_by", "generated_by", "evaluated_by",
)

# Nested FK chains that ultimately reach an Event
NESTED_EVENT_ATTRS = {
    "feedback": ("event",),           # EventFeedbackResponse -> EventFeedback
    "sponsor": ("event",),            # EventSponsorBenefit/Logo/Payment -> EventSponsor
    "survey": ("event",),             # EventSurveyQuestion -> EventSurvey
    "question": ("survey",),          # EventSurveyResponse -> question.survey.event
    "application": ("event",),        # Approval/Rejection/Negotiation -> application
    "sponsorship": ("application",),  # lifecycle records -> sponsorship.application.event
}


def _resolve_event(value, depth=0):
    """Follow FK attributes until an Event instance is found."""
    if depth > 3 or value is None:
        return None
    if isinstance(value, Event):
        return value
    for attr in ("event", "resource", *NESTED_EVENT_ATTRS.keys()):
        nxt = getattr(value, attr, None)
        if isinstance(nxt, Event):
            return nxt
        resolved = _resolve_event(nxt, depth + 1)
        if isinstance(resolved, Event):
            return resolved
    return None


def _event_of(obj):
    if isinstance(obj, Event):
        return obj
    return _resolve_event(obj)


def _can_touch_event(user, event):
    if user.is_authenticated and (user.is_superuser or user.is_staff):
        return True
    if not isinstance(event, Event):
        return False
    if event.created_by_id == user.id:
        return True
    organizer = getattr(event, "event_organizer", None)
    return bool(organizer is not None and organizer.user_id == user.id)


def _owner_matches(owner_value, user):
    """FK value may be a model instance, a raw pk, or absent."""
    if owner_value is None:
        return False
    if isinstance(owner_value, int):
        return owner_value == user.id
    owner_id = getattr(owner_value, "id", None)
    # Authentication.Profile rows proxy a CustomUser; compare the real user id
    if hasattr(owner_value, "user_id"):
        return getattr(owner_value, "user_id", None) == user.id
    return owner_id == user.id


def _record_owner(obj_or_data, user):
    if isinstance(obj_or_data, dict):
        for field in OWNER_FIELDS:
            if field in obj_or_data and _owner_matches(obj_or_data[field], user):
                return True
        return False
    for field in OWNER_FIELDS:
        if _owner_matches(getattr(obj_or_data, field, None), user):
            return True
    return False


class EventResourceWritePermission(BasePermission):
    """Reads stay open. Writes require the related event's creator/organizer,
    platform staff, or the record's own owner for member-scoped resources."""

    message = "You do not have permission to modify this event resource."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if view.action != "create":
            return True
        model = getattr(getattr(view, "queryset", None), "model", None)
        if model is Event:
            # Event creation remains open to authenticated users;
            # created_by is set server-side in perform_create.
            return True
        data = getattr(request, "data", {}) or {}
        event_ref = data.get("event") or data.get("event_id")
        try:
            event = Event.objects.get(pk=event_ref) if event_ref else None
        except (Event.DoesNotExist, TypeError, ValueError):
            event = None
        if _can_touch_event(request.user, event):
            return True
        if any(field in data for field in OWNER_FIELDS):
            return _record_owner(data, request.user)
        self.message = "A valid event reference is required."
        return False

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if _can_touch_event(request.user, _event_of(obj)):
            return True
        return _record_owner(obj, request.user)


class OwnedResourceWritePermission(BasePermission):
    """For profile/follow style resources without an event link: users may
    only mutate records they own."""

    message = "You do not have permission to modify this resource."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if view.action != "create":
            return True
        data = getattr(request, "data", {}) or {}
        if any(field in data for field in OWNER_FIELDS):
            return _record_owner(data, request.user)
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
            return True
        return _record_owner(obj, request.user)


class IsReadOnlyOrAdmin(BasePermission):
    """Read for everyone, writes restricted to platform admins."""

    message = "Only platform administrators may modify this resource."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and
                    (request.user.is_staff or request.user.is_superuser))
