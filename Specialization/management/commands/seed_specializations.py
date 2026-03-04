"""
Management command to seed specialization objects.
Usage: python manage.py seed_specializations
"""
from django.core.management.base import BaseCommand
from Specialization.models import Specialization


SPECIALIZATIONS = [
    {"name": "Computer Science", "description": "Study of computation, algorithms, data structures, and software engineering."},
    {"name": "Data Science & Analytics", "description": "Extracting insights from structured and unstructured data using statistical methods and machine learning."},
    {"name": "Artificial Intelligence", "description": "Building intelligent systems that can reason, learn, and act autonomously."},
    {"name": "Cybersecurity", "description": "Protecting systems, networks, and data from digital attacks and unauthorized access."},
    {"name": "Software Engineering", "description": "Designing, developing, testing, and maintaining software applications and systems."},
    {"name": "Web Development", "description": "Building and maintaining websites and web applications using modern frameworks and tools."},
    {"name": "Mobile Development", "description": "Creating applications for mobile devices including iOS and Android platforms."},
    {"name": "Cloud Computing", "description": "Delivering computing services over the internet including servers, storage, and databases."},
    {"name": "DevOps & SRE", "description": "Combining software development and IT operations for continuous delivery and reliability."},
    {"name": "Machine Learning", "description": "Developing algorithms and models that enable computers to learn from data."},
    {"name": "Blockchain & Web3", "description": "Decentralized technologies, smart contracts, and distributed ledger systems."},
    {"name": "UI/UX Design", "description": "Designing user interfaces and experiences that are intuitive, accessible, and engaging."},
    {"name": "Business Administration", "description": "Managing organizations including strategy, finance, operations, and human resources."},
    {"name": "Marketing & Digital Marketing", "description": "Promoting products and services through digital channels and traditional media."},
    {"name": "Finance & Accounting", "description": "Managing financial resources, reporting, auditing, and investment analysis."},
    {"name": "Entrepreneurship", "description": "Starting, managing, and scaling new business ventures and startups."},
    {"name": "Project Management", "description": "Planning, executing, and closing projects to meet goals within constraints."},
    {"name": "Human Resources", "description": "Recruiting, managing, and developing an organization's workforce."},
    {"name": "Law & Legal Studies", "description": "Understanding legal systems, regulations, contracts, and compliance."},
    {"name": "Medicine & Health Sciences", "description": "Studying human health, diseases, treatments, and healthcare delivery."},
    {"name": "Nursing & Clinical Care", "description": "Providing direct patient care and health management in clinical settings."},
    {"name": "Public Health", "description": "Protecting and improving community health through prevention and education."},
    {"name": "Psychology", "description": "Studying human behavior, cognition, emotions, and mental health."},
    {"name": "Education & Teaching", "description": "Developing curricula, instructional methods, and educational technologies."},
    {"name": "Electrical Engineering", "description": "Designing and developing electrical systems, circuits, and electronic devices."},
    {"name": "Mechanical Engineering", "description": "Designing, manufacturing, and maintaining mechanical systems and machinery."},
    {"name": "Civil Engineering", "description": "Designing and constructing infrastructure including buildings, roads, and bridges."},
    {"name": "Architecture", "description": "Designing buildings, spaces, and environments that are functional and aesthetic."},
    {"name": "Environmental Science", "description": "Studying the environment, ecosystems, and sustainability practices."},
    {"name": "Agriculture & Food Science", "description": "Studying crop production, food processing, and sustainable farming practices."},
    {"name": "Mathematics & Statistics", "description": "Studying numbers, structures, patterns, and quantitative analysis methods."},
    {"name": "Physics", "description": "Understanding matter, energy, and the fundamental forces of nature."},
    {"name": "Chemistry", "description": "Studying substances, their properties, reactions, and transformations."},
    {"name": "Biology & Life Sciences", "description": "Studying living organisms, their structures, functions, and evolution."},
    {"name": "Political Science", "description": "Studying governance, political systems, public policy, and international relations."},
    {"name": "Economics", "description": "Analyzing production, distribution, and consumption of goods and services."},
    {"name": "Sociology", "description": "Studying social behavior, institutions, and the structure of society."},
    {"name": "Communications & Media", "description": "Studying mass communication, journalism, public relations, and media production."},
    {"name": "Graphic Design", "description": "Creating visual content for print, digital media, and branding."},
    {"name": "Fine Arts & Creative Arts", "description": "Exploring creative expression through painting, sculpture, music, and performance."},
    {"name": "Philosophy & Ethics", "description": "Examining fundamental questions about existence, knowledge, and morality."},
    {"name": "Linguistics & Languages", "description": "Studying language structure, acquisition, and multilingual communication."},
    {"name": "History & Cultural Studies", "description": "Examining past events, civilizations, and cultural developments."},
    {"name": "Theology & Religious Studies", "description": "Studying religious traditions, texts, and spiritual practices."},
    {"name": "Social Work", "description": "Helping individuals and communities improve their well-being and access social services."},
    {"name": "Supply Chain & Logistics", "description": "Managing the flow of goods, information, and resources from origin to consumer."},
    {"name": "Real Estate", "description": "Buying, selling, managing, and developing property and land."},
    {"name": "Hospitality & Tourism", "description": "Managing hotels, restaurants, travel, and tourism operations."},
    {"name": "Sports Science & Management", "description": "Studying athletic performance, sports business, and physical fitness."},
    {"name": "Journalism & Investigative Reporting", "description": "Researching, writing, and reporting news and in-depth stories."},
]


class Command(BaseCommand):
    help = "Seed the database with specialization objects"

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing specializations before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            count = Specialization.objects.count()
            Specialization.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {count} existing specializations."))

        created_count = 0
        skipped_count = 0

        for spec_data in SPECIALIZATIONS:
            obj, created = Specialization.objects.get_or_create(
                name=spec_data["name"],
                defaults={"description": spec_data["description"]},
            )
            if created:
                created_count += 1
            else:
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeding complete: {created_count} created, {skipped_count} already existed."
            )
        )
