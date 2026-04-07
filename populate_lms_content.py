import os
import django
import random
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Specialization.models import (
    Specialization, Stack, Lesson, Quiz, QuizQuestion, Certificate
)
from Authentication.models import Profile

def populate_lms():
    print("Starting Learning Management System data population...")
    
    admin_profile = Profile.objects.first()
    if not admin_profile:
        print("No profiles found to assign as author. Aborting.")
        return

    # Helper function to generate lessons for a stack
    def create_lessons(stack, prefix, count=5):
        lessons = []
        content_types = ['video', 'text', 'audio', 'image', 'code', 'file']
        
        for i in range(count):
            c_type = content_types[i % len(content_types)]
            
            lesson = Lesson.objects.create(
                stack=stack,
                title=f"{prefix} - Lesson {i+1}: {c_type.title()} Content",
                description=f"Detailed overview of {prefix} specifically focusing on {c_type}",
                content_type=c_type,
                content_text=f"<h3>Welcome to {prefix} - Lesson {i+1}</h3><p>Enjoy this high-quality learning content designed exclusively for Comrade platform users.</p>",
                video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ" if c_type == 'video' else "",
                audio_url="https://example.com/audio.mp3" if c_type == 'audio' else "",
                image_url=f"https://source.unsplash.com/800x600/?{prefix.replace(' ', ',')},learning",
                code_snippet="def hello_world():\n    print('Hello, Comrade!')\n\nhello_world()" if c_type == 'code' else "",
                code_language="python",
                order=i+1,
                duration_minutes=random.randint(5, 30),
                is_preview=(i == 0),
            )
            lessons.append(lesson)
            
        print(f"  -> Created {count} lessons for stack: {stack.name}")
        return lessons

    # Helper function to generate end-of-module quiz
    def create_quiz(stack, specialization):
        quiz = Quiz.objects.create(
            stack=stack,
            specialization=specialization,
            title=f"Assessment: {stack.name}",
            description=f"Test your knowledge on {stack.name}. Pass this quiz to contribute to your final grade.",
            placement='end_of_module',
            passing_score=70,
            max_attempts=3,
            order=99
        )
        
        # MC Question
        QuizQuestion.objects.create(
            quiz=quiz,
            question_text=f"What is the core principle taught in {stack.name}?",
            question_type='multiple_choice',
            choices=[
                {"label": "A", "text": "Continuous practice", "is_correct": True},
                {"label": "B", "text": "Watching without doing", "is_correct": False},
                {"label": "C", "text": "Skipping documentation", "is_correct": False},
            ],
            explanation="Continuous practice is essential for mastering any new skill.",
            points=10,
            order=1
        )
        
        # True/False
        QuizQuestion.objects.create(
            quiz=quiz,
            question_text=f"{stack.name} is irrelevant to modern industry standards.",
            question_type='true_false',
            choices=[
                {"label": "True", "text": "True", "is_correct": False},
                {"label": "False", "text": "False", "is_correct": True},
            ],
            explanation="These skills are highly relevant today.",
            points=5,
            order=2
        )
        
        # Code challenge
        QuizQuestion.objects.create(
            quiz=quiz,
            question_text="Write a Python function named 'get_status' that returns the string 'active'.",
            question_type='code_challenge',
            correct_answer="def get_status():\n    return 'active'",
            code_template="def get_status():\n    # your code here\n    pass",
            points=15,
            order=3
        )
        print(f"  -> Created quiz for stack: {stack.name}")

    # Process all existing Specializations/Courses/Masterclasses
    specs = Specialization.objects.all()
    count = 0
    for spec in specs:
        # Create a certificate template if it doesn't exist
        cert, _ = Certificate.objects.get_or_create(
            issuer_name="Comrade Academy",
            certificate_type='completion',
            auto_generate=True,
            created_by=admin_profile
        )
        cert.specialization.add(spec)

        for stack in spec.stacks.all():
            # Only add lessons if the stack has none
            if stack.lessons.count() == 0:
                create_lessons(stack, stack.name, count=5)
                create_quiz(stack, spec)
        count += 1
        
    print(f"\nPopulation complete! Processed {count} learning paths with Lessons and Quizzes.")

if __name__ == "__main__":
    populate_lms()
