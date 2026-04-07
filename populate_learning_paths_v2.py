import os
import django
import random
from datetime import datetime
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Authentication.models import CustomUser, Profile
from Specialization.models import Specialization, Stack

def populate():
    print("Expanding Database: 7 Specializations (with 7 stacks each), 7 Courses, 7 Masterclasses...")

    user = CustomUser.objects.first()
    if not user:
        print("No users found.")
        return
        
    profile = Profile.objects.filter(user=user).first()

    specialization_seed = [
        {"name": "Frontend Architecture mastery", "img": "https://images.unsplash.com/photo-1542831371-29b0f74f9713?auto=format&fit=crop&q=80&w=400"},
        {"name": "Backend Python Ninja", "img": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&q=80&w=400"},
        {"name": "Cloud DevOps Professional", "img": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&q=80&w=400"},
        {"name": "Data Science & Deep Learning", "img": "https://images.unsplash.com/photo-1555949963-aa79dcee57d5?auto=format&fit=crop&q=80&w=400"},
        {"name": "Cybersecurity Ethical Hacker", "img": "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?auto=format&fit=crop&q=80&w=400"},
        {"name": "Mobile app development with Flutter", "img": "https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?auto=format&fit=crop&q=80&w=400"},
        {"name": "Blockchain & Web3 Architect", "img": "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?auto=format&fit=crop&q=80&w=400"}
    ]

    course_seed = [
        {"name": "React Hooks & Context Guide", "img": "https://images.unsplash.com/photo-1633356122544-f134324a6cee?auto=format&fit=crop&q=80&w=400"},
        {"name": "Mastering PostgreSQL", "img": "https://images.unsplash.com/photo-1544383835-bda2bc66a55d?auto=format&fit=crop&q=80&w=400"},
        {"name": "Tailwind CSS from Scratch", "img": "https://images.unsplash.com/photo-1507721999472-8ed4421c4af2?auto=format&fit=crop&q=80&w=400"},
        {"name": "Django Rest Framework deep dive", "img": "https://images.unsplash.com/photo-1627398242454-45a1465c2479?auto=format&fit=crop&q=80&w=400"},
        {"name": "Go Lang Microservices", "img": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&q=80&w=400"},
        {"name": "Figma to Code Pipeline", "img": "https://images.unsplash.com/photo-1611162617474-5b21e879e113?auto=format&fit=crop&q=80&w=400"},
        {"name": "Advanced Python Scripting", "img": "https://images.unsplash.com/photo-1562415132-7adecc0485d5?auto=format&fit=crop&q=80&w=400"}
    ]

    masterclass_seed = [
        {"name": "Sam Altman's AI Future", "img": "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&q=80&w=400"},
        {"name": "Naval's Wealth Creation", "img": "https://images.unsplash.com/photo-1553729459-efe14ef6055d?auto=format&fit=crop&q=80&w=400"},
        {"name": "Startup Y-Combinator Series", "img": "https://images.unsplash.com/photo-1556761175-4b46a572b786?auto=format&fit=crop&q=80&w=400"},
        {"name": "Negotiation by Chris Voss", "img": "https://images.unsplash.com/photo-1552581234-26160f608093?auto=format&fit=crop&q=80&w=400"},
        {"name": "System Design with Alex Xu", "img": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&q=80&w=400"},
        {"name": "Leadership by Jocko Willink", "img": "https://images.unsplash.com/photo-1573164713988-8665fc963095?auto=format&fit=crop&q=80&w=400"},
        {"name": "Marketing Strategy with Seth Godin", "img": "https://images.unsplash.com/photo-1557838923-2985c318be48?auto=format&fit=crop&q=80&w=400"}
    ]

    print("Generating 7 Specializations and 49 Stacks...")
    for idx, spec_data in enumerate(specialization_seed):
        s, _ = Specialization.objects.get_or_create(
            name=f"{spec_data['name']} (Expansion {idx})",
            defaults={
                'description': f"Comprehensive path for {spec_data['name']}",
                'learning_type': 'specialization',
                'image_url': spec_data['img'],
                'is_paid': False
            }
        )
        s.created_by.add(profile)
        s.admins.add(profile)

        # Create 7 stacks per specialization
        for i in range(1, 8):
            st, _ = Stack.objects.get_or_create(
                name=f"{spec_data['name']} - Stage {i}",
                defaults={
                    'description': f"Module {i} covering specific skills for {spec_data['name']}.",
                    'image_url': spec_data['img']
                }
            )
            st.created_by.add(profile)
            s.stacks.add(st)
        s.save()

    print("Generating 7 Courses...")
    for idx, c_data in enumerate(course_seed):
        c, _ = Specialization.objects.get_or_create(
            name=f"{c_data['name']} (Expansion {idx})",
            defaults={
                'description': f"Intensive course on {c_data['name']}",
                'learning_type': 'course',
                'image_url': c_data['img'],
                'is_paid': True,
                'price': Decimal('29.99')
            }
        )
        c.created_by.add(profile)
        c.admins.add(profile)
        
        # Give course 2 dummy stacks
        st, _ = Stack.objects.get_or_create(name=f"Course Basics: {c_data['name']}")
        c.stacks.add(st)
        c.save()

    print("Generating 7 Masterclasses...")
    for idx, m_data in enumerate(masterclass_seed):
        m, _ = Specialization.objects.get_or_create(
            name=f"{m_data['name']} (Expansion {idx})",
            defaults={
                'description': f"Premium masterclass on {m_data['name']}",
                'learning_type': 'masterclass',
                'image_url': m_data['img'],
                'is_paid': True,
                'price': Decimal('99.99')
            }
        )
        m.created_by.add(profile)
        m.admins.add(profile)
        m.save()
        
    print("Expanded catalog created successfully!")

if __name__ == '__main__':
    populate()
