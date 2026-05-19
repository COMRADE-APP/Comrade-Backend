"""
Celery tasks for the Research module.
Handles periodic participant matching and compensation reminders.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def run_periodic_matching():
    """
    Periodically run participant matching for all research projects
    that are actively seeking participants.
    Runs daily at 03:00.
    """
    from Research.models import ResearchProject
    from Research.matching import run_matching_for_project

    logger.info("Running periodic participant matching")

    projects = ResearchProject.objects.filter(
        status='seeking_participants',
        seeking_participants=True
    )

    total_matches = 0
    for project in projects:
        try:
            count = run_matching_for_project(project)
            total_matches += count
            logger.info(f"Matched {count} users for project: {project.title}")
        except Exception as e:
            logger.error(f"Failed matching for project {project.id}: {e}")

    logger.info(f"Total matches computed: {total_matches}")
    return f"Total matches: {total_matches}"


@shared_task
def notify_matched_participants():
    """
    Send notifications to matched participants who haven't been notified yet.
    Only notifies users with a match score >= 60.
    Runs daily at 09:30.
    """
    from Research.models import ParticipantMatching
    from Notifications.models import create_notification

    logger.info("Running notify_matched_participants task")
    notified = 0

    unnotified_matches = ParticipantMatching.objects.filter(
        notification_sent=False,
        match_score__gte=60,
        research__status='seeking_participants'
    ).select_related('participant', 'research')[:100]  # Process max 100 per run

    for match in unnotified_matches:
        try:
            create_notification(
                recipient=match.participant,
                notification_type='recommendation',
                title='Research Match Found',
                message=(
                    f"You have a {int(match.match_score)}% match for the research project "
                    f"\"{match.research.title}\". Check it out and apply!"
                ),
                action_url=f"/research/{match.research.id}",
                extra_data={
                    'match_score': match.match_score,
                    'research_id': str(match.research.id)
                }
            )
            match.notification_sent = True
            match.notification_sent_at = timezone.now()
            match.save()
            notified += 1
        except Exception as e:
            logger.error(f"Failed to notify match {match.id}: {e}")

    logger.info(f"Matched participants notified: {notified}")
    return f"Notified: {notified}"


@shared_task
def remind_unpaid_compensation():
    """
    Remind PIs about unpaid compensation for completed participants.
    Runs weekly on Mondays at 10:00.
    """
    from Research.models import ResearchProject, ResearchParticipant
    from Notifications.models import create_notification
    from django.db.models import Sum

    logger.info("Running remind_unpaid_compensation task")
    reminded = 0

    # Find projects with completed but unpaid participants
    projects_with_unpaid = ResearchProject.objects.filter(
        participants__status='completed',
        participants__compensation_paid=False,
        participants__position__compensation_type='monetary'
    ).distinct()

    for project in projects_with_unpaid:
        unpaid = ResearchParticipant.objects.filter(
            research=project,
            status='completed',
            compensation_paid=False
        )
        unpaid_count = unpaid.count()
        total_owed = unpaid.aggregate(
            total=Sum('position__compensation_amount')
        )['total'] or 0

        if unpaid_count > 0:
            try:
                create_notification(
                    recipient=project.principal_investigator,
                    notification_type='system',
                    title='Unpaid Participant Compensation',
                    message=(
                        f"You have {unpaid_count} completed participant(s) in \"{project.title}\" "
                        f"awaiting compensation (total: {total_owed})."
                    ),
                    action_url=f"/research/{project.id}?tab=participants",
                )
                reminded += 1
            except Exception as e:
                logger.error(f"Failed to remind PI for project {project.id}: {e}")

    logger.info(f"PIs reminded: {reminded}")
    return f"Reminded: {reminded}"
