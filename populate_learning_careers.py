import os
import django
import random
from datetime import datetime, timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Authentication.models import CustomUser, Profile
from Specialization.models import Specialization, Stack
from Careers.models import CareerOpportunity, Gig

def populate():
    print("Populating Specializations, Courses, Masterclasses, Careers, and Gigs...")

    user = CustomUser.objects.first()
    if not user:
        print("No users found. Please create a user first.")
        return
        
    profile = Profile.objects.filter(user=user).first()
    if not profile:
        profile = Profile.objects.create(user=user)
        print(f"Created profile for user: {user.email}")

    print(f"Using profile/user: {user.email}")

    # 1. Create Stacks (Modules)
    stack1, _ = Stack.objects.get_or_create(
        name="Frontend Fundamentals",
        defaults={
            'description': "Core fundamentals for frontend development including HTML, CSS, and JS.",
            'image_url': "https://images.unsplash.com/photo-1542831371-29b0f74f9713?auto=format&fit=crop&q=80&w=400"
        }
    )
    stack1.created_by.add(profile)
    
    stack2, _ = Stack.objects.get_or_create(
        name="Advanced React Patterns",
        defaults={
            'description': "Advanced UI patterns using React 18, Server Components, and Tailwind.",
            'image_url': "https://images.unsplash.com/photo-1633356122544-f134324a6cee?auto=format&fit=crop&q=80&w=400"
        }
    )
    stack2.created_by.add(profile)
    
    stack3, _ = Stack.objects.get_or_create(
        name="Machine Learning Basics",
        defaults={
            'description': "Introduction to algorithms, neural networks, and Python data science.",
            'image_url': "https://images.unsplash.com/photo-1555949963-aa79dcee57d5?auto=format&fit=crop&q=80&w=400"
        }
    )
    stack3.created_by.add(profile)

    # 2. Create Specializations (Learning Types)
    
    ## Specialization
    spec, _ = Specialization.objects.get_or_create(
        name="Full-Stack Web Development",
        defaults={
            'description': "A complete path to becoming a full-stack developer.",
            'learning_type': 'specialization',
            'is_paid': False,
            'image_url': "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&q=80&w=400"
        }
    )
    spec.stacks.add(stack1, stack2)
    spec.created_by.add(profile)

    ## Course
    course, _ = Specialization.objects.get_or_create(
        name="React Mastery 2026",
        defaults={
            'description': "Crash course on React.",
            'learning_type': 'course',
            'is_paid': True,
            'price': Decimal('49.99'),
            'image_url': "https://images.unsplash.com/photo-1627398242454-45a1465c2479?auto=format&fit=crop&q=80&w=400"
        }
    )
    course.stacks.add(stack2)
    course.created_by.add(profile)
    
    ## Masterclass
    masterclass, _ = Specialization.objects.get_or_create(
        name="AI Innovations & Strategy",
        defaults={
            'description': "Exclusive insights from industry leaders on AI.",
            'learning_type': 'masterclass',
            'is_paid': True,
            'price': Decimal('199.00'),
            'image_url': "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&q=80&w=400"
        }
    )
    masterclass.stacks.add(stack3)
    masterclass.created_by.add(profile)
    
    print("Created Specializations, Courses, and Masterclasses.")

    # 3. Create Career Opportunities
    career1, _ = CareerOpportunity.objects.get_or_create(
        title="Senior Frontend Engineer",
        defaults={
            'posted_by': user,
            'company_name': 'TechVision Labs',
            'description': 'Looking for an experienced React developer to lead our frontend team.',
            'requirements': '5+ years of React experience, solid understanding of TS and Tailwind.',
            'salary_min': Decimal('120000.00'),
            'salary_max': Decimal('150000.00'),
            'location': 'New York, NY',
            'is_remote': True,
            'job_type': 'full_time',
            'experience_level': 'senior',
            'industry': 'tech',
            'image_url': 'https://images.unsplash.com/photo-1549692520-acc6669e2f0c?auto=format&fit=crop&q=80&w=400'
        }
    )

    career2, _ = CareerOpportunity.objects.get_or_create(
        title="Marketing Specialist",
        defaults={
            'posted_by': user,
            'company_name': 'Global Media Inc',
            'description': 'Join our dynamic marketing team to drive global campaigns.',
            'requirements': 'Degree in Marketing, 2+ years of SEO/SEM experience.',
            'salary_min': Decimal('60000.00'),
            'salary_max': Decimal('85000.00'),
            'location': 'London, UK',
            'is_remote': False,
            'job_type': 'full_time',
            'experience_level': 'mid',
            'industry': 'marketing',
        }
    )
    
    print("Created Career Opportunities.")

    # 4. Create Gigs
    gig1, _ = Gig.objects.get_or_create(
        title="Design a Landing Page",
        defaults={
            'creator': user,
            'description': 'Need a modern, responsive landing page for my new startup.',
            'requirements': 'Figma expertise, basic understanding of web design trends.',
            'pay_amount': Decimal('500.00'),
            'pay_timing': 'after',
            'industry': 'design',
            'location': 'Remote',
            'is_remote': True,
            'status': 'open',
            'deadline': datetime.now() + timedelta(days=14)
        }
    )
    
    gig2, _ = Gig.objects.get_or_create(
        title="Python Data Scraping Script",
        defaults={
            'creator': user,
            'description': 'Need a python script to scrape some e-commerce data.',
            'requirements': 'Python, Scrapy, BeautifulSoup.',
            'pay_amount': Decimal('250.00'),
            'pay_timing': 'milestone',
            'industry': 'tech',
            'location': 'Remote',
            'is_remote': True,
            'status': 'open',
            'deadline': datetime.now() + timedelta(days=5)
        }
    )
    
    print("Created Gigs.")
    print("Population successful!")

if __name__ == '__main__':
    populate()
