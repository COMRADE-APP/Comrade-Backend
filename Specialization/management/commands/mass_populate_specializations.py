import random
from django.core.management.base import BaseCommand
from Authentication.models import CustomUser, Profile
from Specialization.models import Specialization, Stack

class Command(BaseCommand):
    help = 'Populates the DB with 55 Specializations and 55 Stacks using loremflickr for accurate images'

    def handle(self, *args, **options):
        # We need at least one profile to act as creator
        user = CustomUser.objects.filter(is_active=True).first()
        if not user:
            self.stdout.write(self.style.ERROR("No active user found. Cannot proceed."))
            return
        profile, created = Profile.objects.get_or_create(user=user)

        # 55 Specializations
        spec_data = [
            ("Full Stack Web Development", "programming,code"),
            ("Data Science & Machine Learning", "data,science"),
            ("Mobile App Development (iOS/Android)", "mobile,app"),
            ("Cloud Computing Fundamentals", "cloud,server"),
            ("Cybersecurity Essentials", "security,hacker"),
            ("UI/UX Design Masterclass", "design,interface"),
            ("Digital Marketing & SEO", "marketing,digital"),
            ("Business Analytics & Intelligence", "business,chart"),
            ("Blockchain & Cryptocurrency", "crypto,blockchain"),
            ("Artificial Intelligence Deep Dive", "ai,robot"),
            ("DevOps Engineering Practices", "devops,server"),
            ("Game Development with Unity", "game,development"),
            ("Embedded Systems & IoT", "electronics,iot"),
            ("Software Testing & QA", "testing,quality"),
            ("Database Administration", "database,server"),
            ("Graphic Design & Illustration", "graphic,art"),
            ("Video Editing & Production", "video,editing"),
            ("3D Modeling & Animation", "3d,animation"),
            ("Project Management Professional", "project,management"),
            ("Agile & Scrum Methodologies", "agile,scrum"),
            ("Financial Modeling & Analysis", "finance,money"),
            ("Accounting & Bookkeeping", "accounting,finance"),
            ("Human Resources Management", "hr,people"),
            ("Sales & Negotiation Skills", "sales,deal"),
            ("Public Speaking & Communication", "speech,communication"),
            ("Creative Writing Workshop", "writing,book"),
            ("Journalism & Media Studies", "journalism,news"),
            ("Foreign Language: Spanish", "spanish,language"),
            ("Foreign Language: Mandarin", "chinese,language"),
            ("Foreign Language: French", "french,language"),
            ("Photography Masterclass", "photography,camera"),
            ("Music Production Basics", "music,production"),
            ("Cooking & Culinary Arts", "cooking,food"),
            ("Baking & Pastry Arts", "baking,cake"),
            ("Fitness & Personal Training", "fitness,gym"),
            ("Yoga & Mindfulness Retreat", "yoga,meditation"),
            ("Nutrition & Dietetics", "nutrition,food"),
            ("Psychology & Human Behavior", "psychology,brain"),
            ("Sociology Basics", "sociology,people"),
            ("History of Western Civilization", "history,ancient"),
            ("Political Science Fundamentals", "politics,government"),
            ("Law & Legal Studies", "law,justice"),
            ("Economics: Micro & Macro", "economics,money"),
            ("Mathematics for Machine Learning", "math,equation"),
            ("Physics: Classical & Quantum", "physics,science"),
            ("Chemistry & Lab Techniques", "chemistry,lab"),
            ("Biology & Genetics", "biology,dna"),
            ("Environmental Science", "environment,nature"),
            ("Astronomy & Space Exploration", "astronomy,space"),
            ("Architecture & Urban Design", "architecture,building"),
            ("Interior Design Strategies", "interior,design"),
            ("Fashion Design & Textiles", "fashion,clothes"),
            ("Automotive Engineering", "car,engine"),
            ("Aviation & Aeronautics", "airplane,flight"),
            ("Maritime Navigation", "ship,ocean")
        ]

        # 55 Stacks
        stack_data = [
            ("MERN Stack Absolute Basics", "programming,react"),
            ("MEAN Stack Deep Dive", "programming,angular"),
            ("LAMP Stack Essentials", "server,linux"),
            ("Python Data Analysis Stack", "python,data"),
            ("R Statistical Computing Stack", "statistics,chart"),
            ("Go Language Microservices", "golang,server"),
            ("Ruby on Rails Web Dev", "ruby,code"),
            ("Django & React Full Stack", "django,react"),
            ("Spring Boot Java Enterprise", "java,enterprise"),
            ("C# .NET Core Development", "csharp,code"),
            ("Flutter Cross-Platform Mobile", "flutter,mobile"),
            ("React Native Expert Path", "react,mobile"),
            ("AWS Cloud Architect Stack", "aws,cloud"),
            ("Azure Solutions Provider", "azure,cloud"),
            ("Google Cloud Platform Basics", "gcp,cloud"),
            ("Docker & Kubernetes Containerization", "docker,container"),
            ("Jenkins CI/CD Pipeline", "jenkins,pipeline"),
            ("Terraform Infrastructure as Code", "terraform,infrastructure"),
            ("Ansible Configuration Management", "ansible,server"),
            ("Ethical Hacking Toolset", "hacker,security"),
            ("Network Penetration Testing", "network,security"),
            ("Figma Design Systems", "figma,design"),
            ("Adobe Creative Cloud Mastery", "adobe,art"),
            ("Google Analytics & Tag Manager", "analytics,google"),
            ("Facebook Ads & Marketing", "facebook,marketing"),
            ("Salesforce Admin Certification", "salesforce,crm"),
            ("HubSpot Inbound Marketing", "hubspot,marketing"),
            ("Ethereum Smart Contracts (Solidity)", "ethereum,crypto"),
            ("Web3.js & DApp Development", "web3,blockchain"),
            ("TensorFlow & Keras Deep Learning", "tensorflow,ai"),
            ("PyTorch Advanced Research", "pytorch,ai"),
            ("Unreal Engine Blueprints", "unreal,game"),
            ("Arduino Maker Projects", "arduino,electronics"),
            ("Raspberry Pi Computing", "raspberrypi,computer"),
            ("Selenium Automated Testing", "selenium,testing"),
            ("Jest & React Testing Library", "jest,testing"),
            ("MySQL Database Mastery", "mysql,database"),
            ("PostgreSQL Advanced Queries", "postgresql,database"),
            ("MongoDB NoSQL Architect", "mongodb,database"),
            ("Redis Caching Patterns", "redis,database"),
            ("Elasticsearch & Kibana", "elasticsearch,data"),
            ("GraphQL API Development", "graphql,api"),
            ("RESTful API Design", "rest,api"),
            ("WebSockets Real-Time Comm", "websocket,chat"),
            ("System Design Interview Prep", "system,design"),
            ("Data Structures & Algorithms", "algorithm,code"),
            ("Competitive Programming", "contest,programming"),
            ("Excel Advanced Macros & VBA", "excel,spreadsheet"),
            ("Power BI Interactive Dashboards", "powerbi,chart"),
            ("Tableau Visual Analytics", "tableau,chart"),
            ("WordPress Theme Development", "wordpress,blog"),
            ("Shopify E-commerce Setup", "shopify,store"),
            ("Unity 2D Platformer Dev", "unity,game"),
            ("Blender 3D Sculpting", "blender,3d"),
            ("Video Premiere Pro Editing", "premiere,video")
        ]

        total_specs = 0
        total_stacks = 0

        # Create Specializations
        for i, (name, keywords) in enumerate(spec_data):
            img_url = f"https://loremflickr.com/600/400/{keywords}?lock={i+500}"
            spec, created = Specialization.objects.update_or_create(
                name=name,
                defaults={
                    'description': f"Master the art of {name} with comprehensive guides, tasks, and real-world examples.",
                    'image_url': img_url
                }
            )
            spec.created_by.add(profile)
            total_specs += 1
            if i % 10 == 0:
                self.stdout.write(f"Processed {i} Specializations...")

        # Create Stacks
        for i, (name, keywords) in enumerate(stack_data):
            img_url = f"https://loremflickr.com/600/400/{keywords}?lock={i+600}"
            stack, created = Stack.objects.update_or_create(
                name=name,
                defaults={
                    'description': f"Dive into the {name} technologies and build robust implementations.",
                    'image_url': img_url
                }
            )
            stack.created_by.add(profile)
            total_stacks += 1
            if i % 10 == 0:
                self.stdout.write(f"Processed {i} Stacks...")

        # Optionally link some stacks to specializations randomly to show relationships
        specializations = list(Specialization.objects.all())
        stacks = list(Stack.objects.all())
        link_count = 0
        
        for spec in specializations:
            # Pick 2-5 random stacks for each specialization
            assigned_stacks = random.sample(stacks, random.randint(2, 5))
            for st in assigned_stacks:
                spec.stacks.add(st)
                link_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully populated {total_specs} Specializations and {total_stacks} Stacks! ({link_count} relationships built)'))
