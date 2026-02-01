"""
QomAI Views
API endpoints for chat, recommendations, and ML features
"""
import os
import json
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Conversation, Message, UserPreference, ContentAnalysis
from .serializers import (
    ConversationSerializer, ConversationListSerializer,
    MessageSerializer, UserPreferenceSerializer,
    ContentAnalysisSerializer, ChatRequestSerializer, ChatResponseSerializer
)
from .services.deepseek_service import QomAIService
from .services.web_search_service import web_search_service


class ChatView(APIView):
    """
    Main chat endpoint for QomAI with web search and file support
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def post(self, request):
        # Handle FormData parsing (history comes as string)
        data = request.data.copy()
        if 'history' in data and isinstance(data['history'], str):
            try:
                data['history'] = json.loads(data['history'])
            except json.JSONDecodeError:
                data['history'] = []
                
        serializer = ChatRequestSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user_message = serializer.validated_data['message']
        history = serializer.validated_data.get('history', [])
        conversation_id = serializer.validated_data.get('conversation_id')
        model = data.get('model', 'qwen-7b')
        enable_search = data.get('enable_search', True)
        
        # Handle File Uploads
        file_content = ""
        if request.FILES:
            file_content = "\n\n**Attached Files Content:**\n"
            for key, file in request.FILES.items():
                try:
                    # Read text files
                    if file.content_type.startswith('text/') or file.name.endswith(('.txt', '.md', '.py', '.js', '.csv', '.json')):
                        content = file.read().decode('utf-8', errors='ignore')
                        file_content += f"\n--- File: {file.name} ---\n{content}\n"
                    # Simple PDF handling (if pypdf logic added later, for now just note it)
                    elif file.name.endswith('.pdf'):
                        # TODO: Add PDF text extraction
                        file_content += f"\n--- File: {file.name} (PDF Content Extraction Pending) ---\n"
                    else:
                        file_content += f"\n--- File: {file.name} (Binary File) ---\n"
                except Exception as e:
                    file_content += f"\nError reading {file.name}: {str(e)}\n"
        
        # Determine full user context
        full_user_content = user_message + file_content
        
        # Get or create conversation
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id, user=request.user)
            except Conversation.DoesNotExist:
                conversation = Conversation.objects.create(
                    user=request.user,
                    title=user_message[:50]
                )
        else:
            conversation = Conversation.objects.create(
                user=request.user,
                title=user_message[:50]
            )
        
        # Save user message (store original msg + generic file note)
        display_content = user_message
        if request.FILES:
            filenames = [f.name for f in request.FILES.values()]
            display_content += f"\n\n[Attached: {', '.join(filenames)}]"

        Message.objects.create(
            conversation=conversation,
            role='user',
            content=display_content
        )
        
        # Check if web search is needed (only if no files attached, usually)
        search_results = None
        search_context = ""
        
        # Don't search if analyzing files, unless explicitly asked
        should_search = enable_search and web_search_service.should_search(user_message)
        if request.FILES and "search" not in user_message.lower():
            should_search = False
            
        if should_search:
            try:
                search_results = web_search_service.search(user_message, num_results=5)
                if search_results:
                    search_context = web_search_service.format_results_for_context(search_results)
            except Exception as e:
                print(f"Web search failed: {e}")
        
        # Build context for AI
        system_prompt = self._build_system_prompt(request.user, has_search=bool(search_context))
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history
        for msg in history[-10:]:  # Last 10 messages for context
            if msg.get('role') in ['user', 'assistant']:
                messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
        
        # Construct final prompt for AI
        final_prompt = full_user_content
        if search_context:
            final_prompt = f"""User Question: {user_message}

{file_content}

I've searched the web for current information. Here are the results:

{search_context}

Please use these search results and the attached files (if any) to provide an accurate answer."""
        elif file_content:
             final_prompt = f"""{user_message}

{file_content}"""

        messages.append({"role": "user", "content": final_prompt})
        
        # Create service with requested model
        service = QomAIService()
        if model and model in service.QWEN_MODELS:
            service.model = service.QWEN_MODELS[model]
            service.model_key = model
        
        # Get AI response
        response = service.chat_completion(messages)
        
        # Save assistant message
        assistant_message = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=response['content'],
            tokens_used=response.get('tokens_used'),
            model_used=response.get('model', '')
        )
        
        return Response({
            'message': response['content'],
            'conversation_id': str(conversation.id),
            'tokens_used': response.get('tokens_used', 0),
            'model': response.get('model', ''),
            'searched': bool(search_results),
            'search_count': len(search_results) if search_results else 0
        })
    
    def _build_system_prompt(self, user, has_search=False):
        """Build a context-aware system prompt"""
        name = user.first_name or user.email.split('@')[0]
        current_date = datetime.now().strftime("%B %d, %Y")
        
        search_instruction = ""
        if has_search:
            search_instruction = """
IMPORTANT: You have access to current web search results. Use them to provide accurate, up-to-date information.
When answering questions about current events, news, or anything after October 2023, prioritize the search results.
Always cite sources when using information from search results."""
        
        return f"""You are QomAI, an intelligent AI assistant for the Comrade platform with web search and file analysis capabilities.
You are helpful, friendly, and knowledgeable about both the platform and current events.

Current Date: {current_date}
User: {name}
{search_instruction}

Platform Features:
- Rooms: Collaborative discussion spaces
- Events: Platform activities and gatherings
- Articles: User-published content and blog posts
- Research: Academic and professional research papers
- Opinions: Short-form social posts (like tweets)
- Learning Paths: Structured educational programs
- Payment Groups: Collaborative savings and payments
- Organizations & Institutions: Professional entities

Guidelines:
1. Be helpful and concise
2. Provide specific, actionable guidance
3. Reference platform features when relevant
4. Be friendly but professional
5. Admit when you don't know something
6. Use markdown formatting for better readability
7. Use bullet points and headers when listing information
8. For current events or recent news, use provided search results
9. When analyzing files, refer to the content provided in the message"""


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user).order_by('-updated_at')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ChatHistoryView(APIView):
    """
    Get recent chat history
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        conversations = Conversation.objects.filter(
            user=request.user,
            is_active=True
        ).order_by('-updated_at')[:20]
        
        serializer = ConversationListSerializer(conversations, many=True)
        return Response(serializer.data)


class UserPreferenceView(APIView):
    """
    Get/update user preferences for QomAI
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        preference, created = UserPreference.objects.get_or_create(
            user=request.user,
            defaults={'preferred_model': 'qwen-7b'}
        )
        return Response({
            'preferred_model': preference.preferred_model,
            'created': created
        })
    
    def post(self, request):
        preferred_model = request.data.get('preferred_model', 'qwen-7b')
        
        preference, created = UserPreference.objects.update_or_create(
            user=request.user,
            defaults={'preferred_model': preferred_model}
        )
        
        return Response({
            'preferred_model': preference.preferred_model,
            'updated': not created
        })


class WebSearchView(APIView):
    """
    Direct web search endpoint
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        query = request.data.get('query', '')
        num_results = request.data.get('num_results', 5)
        
        if not query:
            return Response(
                {'error': 'Query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            results = web_search_service.search(query, num_results)
            return Response({
                'query': query,
                'results': results,
                'count': len(results)
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FakeNewsAnalysisView(APIView):
    """
    Analyze content for potential fake news/misinformation
    Uses ML model when available, falls back to heuristics
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        content = request.data.get('content', '')
        
        if not content:
            return Response(
                {'error': 'Content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # TODO: Integrate actual ML model
        result = {
            'is_potentially_fake': False,
            'confidence': 0.0,
            'indicators': [],
            'message': 'ML model not yet trained. This is a placeholder response.'
        }
        
        analysis = ContentAnalysis.objects.create(
            user=request.user,
            analysis_type='fake_news',
            input_content=content[:1000],
            result=result,
            confidence_score=result['confidence']
        )
        
        return Response(result)


class RecommendationsView(APIView):
    """
    Get personalized recommendations
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        rec_type = request.query_params.get('type', 'all')
        
        return Response({
            'type': rec_type,
            'recommendations': [],
            'message': 'Recommender system not yet implemented.'
        })


class GenerateLearningPathView(APIView):
    """
    Generate personalized learning path suggestions
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        preferences = request.data
        
        return Response({
            'path': [],
            'message': 'Learning path generator not yet implemented.'
        })


class GenerateTestView(APIView):
    """
    Generate test questions for a topic
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        topic = request.data.get('topic', '')
        count = request.data.get('count', 10)
        difficulty = request.data.get('difficulty', 'medium')
        
        if not topic:
            return Response(
                {'error': 'Topic is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        prompt = f"""Generate {count} {difficulty} difficulty multiple choice questions about: {topic}

Format each question as:
Q: [Question]
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Correct: [Letter]

Be educational and clear."""

        service = QomAIService()
        messages = [
            {"role": "system", "content": "You are an educational content creator."},
            {"role": "user", "content": prompt}
        ]
        
        response = service.chat_completion(messages, temperature=0.8)
        
        return Response({
            'topic': topic,
            'difficulty': difficulty,
            'questions_raw': response['content'],
            'model': response.get('model', '')
        })
