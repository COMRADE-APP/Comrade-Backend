"""
Participant Matching Algorithm for Research Projects.

Computes a 0-100 compatibility score between a user profile and a research
project's participant requirements. The score is a weighted combination of
sub-scores covering demographics, education, skills, location, and availability.
"""
import logging
from datetime import date
from Research.models import ParticipantMatching, ParticipantRequirements

logger = logging.getLogger(__name__)

# Weights for each matching dimension (must sum to 100)
WEIGHTS = {
    'age': 15,
    'education': 25,
    'experience': 25,
    'availability': 15,
    'location': 20,
}

EDUCATION_LEVELS = {
    'any': 0,
    'high_school': 1,
    'associate': 2,
    'bachelor': 3,
    'master': 4,
    'doctoral': 5,
}


def compute_match_score(user, research_project):
    """
    Compute the compatibility score between a user (CustomUser) and a ResearchProject.
    Returns a dict with sub-scores and total_score (0-100).
    """
    try:
        requirements = research_project.requirements.first()
    except ParticipantRequirements.DoesNotExist:
        requirements = None

    if not requirements:
        # No specific requirements — everyone is a perfect match
        return {
            'total_score': 80.0,
            'age_match': 100.0,
            'education_match': 100.0,
            'experience_match': 50.0,
            'availability_match': 100.0,
            'location_match': 50.0,
        }

    profile = getattr(user, 'profile', None)

    age_score = _score_age(user, profile, requirements)
    education_score = _score_education(user, profile, requirements)
    experience_score = _score_experience(user, profile, requirements)
    availability_score = _score_availability(user, profile, requirements)
    location_score = _score_location(user, profile, requirements)

    total = (
        age_score * WEIGHTS['age'] / 100 +
        education_score * WEIGHTS['education'] / 100 +
        experience_score * WEIGHTS['experience'] / 100 +
        availability_score * WEIGHTS['availability'] / 100 +
        location_score * WEIGHTS['location'] / 100
    )

    return {
        'total_score': round(total, 2),
        'age_match': round(age_score, 2),
        'education_match': round(education_score, 2),
        'experience_match': round(experience_score, 2),
        'availability_match': round(availability_score, 2),
        'location_match': round(location_score, 2),
    }


def _score_age(user, profile, requirements):
    """Score based on age range fit."""
    if not requirements.min_age and not requirements.max_age:
        return 100.0  # No age requirement

    dob = getattr(profile, 'date_of_birth', None) if profile else None
    if not dob:
        return 50.0  # Unknown — neutral score

    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    min_age = requirements.min_age or 0
    max_age = requirements.max_age or 200

    if min_age <= age <= max_age:
        return 100.0
    elif age < min_age:
        diff = min_age - age
        return max(0, 100 - diff * 10)
    else:
        diff = age - max_age
        return max(0, 100 - diff * 10)


def _score_education(user, profile, requirements):
    """Score based on education level match."""
    required_level = requirements.min_education_level
    if not required_level or required_level == 'any':
        return 100.0

    # Try to get user's education level from profile
    user_level = getattr(profile, 'education_level', None) if profile else None
    if not user_level:
        return 40.0  # Unknown — below neutral

    req_num = EDUCATION_LEVELS.get(required_level, 0)
    user_num = EDUCATION_LEVELS.get(user_level, 0)

    if user_num >= req_num:
        return 100.0
    else:
        diff = req_num - user_num
        return max(0, 100 - diff * 25)


def _score_experience(user, profile, requirements):
    """Score based on required skills and experience overlap."""
    required_skills = requirements.required_skills or []
    if not required_skills:
        return 80.0  # No specific skills required

    # Get user's skills from profile
    user_skills = []
    if profile:
        user_skills = getattr(profile, 'skills', []) or []
        if isinstance(user_skills, str):
            user_skills = [s.strip().lower() for s in user_skills.split(',')]

    if not user_skills:
        return 30.0

    # Normalize
    required_lower = [s.lower() for s in required_skills]
    user_lower = [s.lower() for s in user_skills]

    # Calculate overlap
    matches = sum(1 for skill in required_lower if any(skill in us or us in skill for us in user_lower))
    overlap_ratio = matches / len(required_lower) if required_lower else 0.0

    return min(100.0, overlap_ratio * 100)


def _score_availability(user, profile, requirements):
    """Score based on time commitment fit."""
    min_hours = requirements.min_hours_per_week
    if not min_hours:
        return 100.0

    # We don't currently store weekly availability on profiles,
    # so default to a neutral score. This can be refined when
    # the profile model includes availability data.
    return 70.0


def _score_location(user, profile, requirements):
    """Score based on location requirements."""
    location_req = requirements.location_requirements
    if not location_req or location_req.strip().lower() in ['any', 'remote', 'n/a', '']:
        return 100.0

    user_location = ''
    if profile:
        user_location = getattr(profile, 'location', '') or getattr(profile, 'city', '') or ''

    if not user_location:
        return 50.0

    # Simple string matching
    if location_req.lower() in user_location.lower() or user_location.lower() in location_req.lower():
        return 100.0

    return 30.0


def run_matching_for_project(research_project):
    """
    Run the matching algorithm for all users against a specific research project.
    Creates/updates ParticipantMatching records for the top matches.
    """
    from Authentication.models import CustomUser

    logger.info(f"Running participant matching for: {research_project.title}")
    
    users = CustomUser.objects.filter(is_active=True)
    matches_created = 0

    for user in users:
        # Skip the PI themselves
        if user == research_project.principal_investigator:
            continue

        scores = compute_match_score(user, research_project)

        # Only create matches above a threshold (e.g., 40+)
        if scores['total_score'] >= 40:
            ParticipantMatching.objects.update_or_create(
                participant=user,
                research=research_project,
                defaults={
                    'match_score': scores['total_score'],
                    'age_match': scores['age_match'],
                    'education_match': scores['education_match'],
                    'experience_match': scores['experience_match'],
                    'availability_match': scores['availability_match'],
                    'location_match': scores['location_match'],
                    'matching_criteria': scores,
                }
            )
            matches_created += 1

    logger.info(f"Created/updated {matches_created} matches for {research_project.title}")
    return matches_created
