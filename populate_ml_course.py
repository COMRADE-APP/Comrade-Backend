import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Specialization.models import (
    Specialization, Stack, Lesson, Quiz, QuizQuestion, Certificate
)
from Authentication.models import Profile

def populate_ml_ai():
    print("Starting ML/AI course creation...")
    
    admin_profile = Profile.objects.first()
    if not admin_profile:
        print("No profiles found to assign as author.")
        return

    # Create the Specialization
    spec, created = Specialization.objects.get_or_create(
        name="Advanced Machine Learning & AI Practitioner",
        learning_type='course',
        defaults={
            'description': "Dive deep into Neural Networks, Deep Learning, Transformers, and GenAI. This comprehensive course prepares you to build cutting-edge AI systems from scratch.",
            'is_paid': True,
            'price': 250.00,
            'image_url': 'https://images.unsplash.com/photo-1555949963-aa79dcee981c?auto=format&fit=crop&q=80&w=1000'
        }
    )
    spec.created_by.add(admin_profile)

    cert, _ = Certificate.objects.get_or_create(
        issuer_name="Data Intelligence Institute",
        certificate_type='completion',
        auto_generate=True,
        created_by=admin_profile
    )
    cert.specialization.add(spec)

    # Delete old stacks for clean slate
    spec.stacks.all().delete()

    stacks_data = [
        ("Module 1: Foundations of Deep Learning", "Understand the mathematics and logic behind neural networks."),
        ("Module 2: NLP and Transformers", "Master Large Language Models, GPT architecture, and Attention mechanisms."),
        ("Module 3: Computer Vision", "Image classification, object detection and generation using CNNs and GANs.")
    ]

    for order, (s_name, s_desc) in enumerate(stacks_data, start=1):
        stack = Stack.objects.create(
            name=s_name,
            description=s_desc,
            image_url='https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&q=80&w=800'
        )
        stack.created_by.add(admin_profile)
        spec.stacks.add(stack)

        # Create mixed-content Lessons for each Stack
        for i in range(1, 4):
            lesson = Lesson.objects.create(
                stack=stack,
                title=f"Lesson {i}: The Theory and Application",
                description=f"Detailed breakdown of topic {i} in {s_name}",
                content_type='video',
                content_text=f"""
                <h3>Introduction to Topic {i}</h3>
                <p>Welcome to this immersive lesson! Below you will find a video lecture, some readable context, and code snippets.</p>
                <div class='bg-gray-800 p-4 rounded-xl mt-4'>
                    <strong>Key Takeaways:</strong>
                    <ul class='list-disc pl-5'>
                        <li>Gradient Descent optimization</li>
                        <li>Backpropagation mechanics</li>
                        <li>Data normalization strategies</li>
                    </ul>
                </div>
                <p class='mt-4'>Make sure to listen to the audio pod-chat below and review the code snippet to solidify your understanding.</p>
                """,
                video_url="https://www.youtube.com/watch?v=aircAruvnKk", # 3Blue1Brown Neural Network
                audio_url="https://actions.google.com/sounds/v1/nature/ocean_waves.ogg",
                image_url="https://images.unsplash.com/photo-1509228468518-180dd4864904?auto=format&fit=crop&w=800&q=80",
                code_snippet=f"# Implement the logic for topic {i}\nimport torch\nimport torch.nn as nn\n\nmodel = nn.Sequential(\n    nn.Linear(64, 128),\n    nn.ReLU(),\n    nn.Linear(128, 10)\n)\n\nprint(model)",
                code_language="python",
                order=i,
                duration_minutes=25 * i,
                is_preview=(i == 1 and order == 1), # Make first lesson free
            )
            print(f"Created Lesson {i} for {stack.name}")

        # Add an end of module quiz
        quiz = Quiz.objects.create(
            stack=stack,
            specialization=spec,
            title=f"Technical Assessment: {stack.name}",
            passing_score=80,
            order=99
        )
        QuizQuestion.objects.create(
            quiz=quiz,
            question_text="What activation function solves the vanishing gradient problem effectively?",
            question_type='multiple_choice',
            choices=[
                {"label": "A", "text": "Sigmoid", "is_correct": False},
                {"label": "B", "text": "ReLU", "is_correct": True},
                {"label": "C", "text": "Tanh", "is_correct": False},
            ],
            points=10, order=1
        )
        QuizQuestion.objects.create(
            quiz=quiz,
            question_text="Deep Learning requires large amounts of labeled data for supervised tasks.",
            question_type='true_false',
            choices=[
                {"label": "True", "text": "True", "is_correct": True},
                {"label": "False", "text": "False", "is_correct": False},
            ],
            points=10, order=2
        )
    
    print("✅ ML & AI Course created successfully!")
    print(f"Course ID: {spec.id}")

if __name__ == "__main__":
    populate_ml_ai()
