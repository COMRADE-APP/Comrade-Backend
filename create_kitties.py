import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "comrade.settings")
django.setup()

from Authentication.models import Profile
from Specialization.models import Specialization
from Payment.models import PaymentGroups, PaymentProfile
from django.contrib.contenttypes.models import ContentType

def run():
    ctype = ContentType.objects.get_for_model(Specialization)
    courses = Specialization.objects.all()
    
    # Fallback to the first available payment profile if a course lacks a creator
    fallback_creator = PaymentProfile.objects.first()

    count = 0
    for course in courses:
        exists = PaymentGroups.objects.filter(entity_content_type=ctype, entity_object_id=str(course.id)).exists()
        if not exists:
            creator_profile = course.created_by.first()
            payment_profile = None
            if creator_profile:
                payment_profile = PaymentProfile.objects.filter(user=creator_profile).first()
            
            if not payment_profile:
                payment_profile = fallback_creator
                
            if payment_profile:
                PaymentGroups.objects.create(
                    name=f"Kitty: {course.name}",
                    description=f"Revenue pool for {course.name}",
                    creator=payment_profile,
                    group_type='kitty',
                    tier=payment_profile.tier,
                    entity_content_type=ctype,
                    entity_object_id=str(course.id),
                    auto_create_room=False
                )
                count += 1
                print(f"Created kitty for: {course.name}")
    print(f'\nTotal kitties created: {count}')

if __name__ == '__main__':
    run()
