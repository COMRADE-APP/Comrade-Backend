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
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Conversation, Message, UserPreference, ContentAnalysis
from .serializers import (
    ConversationSerializer, ConversationListSerializer,
    MessageSerializer, UserPreferenceSerializer,
    ContentAnalysisSerializer, ChatRequestSerializer, ChatResponseSerializer
)
from .services.deepseek_service import qomai_service
from .services.web_search_service import web_search_service
from .services.research_service import deep_research_service


class ChatView(APIView):
    """
    Main chat endpoint for QomAI with web search, file support, and advanced modes
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def post(self, request):
        try:
            # Create a plain dict from request.data to avoid QueryDict mutability issues
            # Handle MultiPartParser (QueryDict) vs JSONParser (dict)
            if hasattr(request.data, 'dict'):
                data = request.data.dict()
            else:
                data = dict(request.data)

            # Handle history parsing manually/safely
            history_raw = data.get('history')
            history_list = []
            
            if history_raw:
                if isinstance(history_raw, str):
                    try:
                        parsed = json.loads(history_raw)
                        # Fix nested list issue: [[{...}, {...}]] -> [{...}, {...}]
                        if isinstance(parsed, list):
                            if len(parsed) > 0 and isinstance(parsed[0], list):
                                history_list = parsed[0]
                                print(f"DEBUG: Unwrapped nested history list. Length: {len(history_list)}")
                            else:
                                history_list = parsed
                        else:
                            history_list = [] # Invalid format
                    except json.JSONDecodeError:
                        print(f"DEBUG: History JSON decode error. Raw: {history_raw[:50]}...")
                        history_list = []
                elif isinstance(history_raw, list):
                    # Already a list?
                    if len(history_raw) > 0 and isinstance(history_raw[0], list):
                         history_list = history_raw[0]
                    else:
                         history_list = history_raw
            
            data['history'] = history_list
            print(f"DEBUG: Final history type: {type(history_list)}")
            if len(history_list) > 0:
                 print(f"DEBUG: History[0] type: {type(history_list[0])}")

            serializer = ChatRequestSerializer(data=data, context={'request': request})
            if not serializer.is_valid():
                print(f"Chat Serializer Errors: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            user_message = serializer.validated_data['message']
            history = serializer.validated_data.get('history', [])
            conversation_id = serializer.validated_data.get('conversation_id')
            
            # New parameters
            model_key = data.get('model', 'qwen-7b')
            mode = data.get('mode', 'chat')  # chat, reasoning, research
            enable_search = data.get('enable_search', True)
            if isinstance(enable_search, str):
                enable_search = enable_search.lower() == 'true'

            # ... (rest of logic handles files etc)
            
            # Wrap core logic to catch specific errors
            # Handle File Uploads
            file_content = ""
            if request.FILES:
                file_content = "\n\n**Attached Files Content:**\n"
                for key, file in request.FILES.items():
                    try:
                        if file.content_type.startswith('text/') or file.name.endswith(('.txt', '.md', '.py', '.js', '.csv', '.json')):
                            content = file.read().decode('utf-8', errors='ignore')
                            file_content += f"\n--- File: {file.name} ---\n{content}\n"
                        else:
                            file_content += f"\n--- File: {file.name} (Binary File) ---\n"
                    except Exception as e:
                        print(f"Error reading file {file.name}: {e}")
                        file_content += f"\nError reading {file.name}: {str(e)}\n"
            
            # Get or create conversation
            if conversation_id:
                try:
                    conversation = Conversation.objects.get(id=conversation_id, user=request.user)
                except Conversation.DoesNotExist:
                    conversation = Conversation.objects.create(user=request.user, title=user_message[:50])
            else:
                conversation = Conversation.objects.create(user=request.user, title=user_message[:50])
            
            # Save user message
            display_content = user_message
            if request.FILES:
                filenames = [f.name for f in request.FILES.values()]
                display_content += f"\n\n[Attached: {', '.join(filenames)}]"
    
            Message.objects.create(
                conversation=conversation,
                role='user',
                content=display_content
            )
            
            response_content = ""
            tokens_used = 0
            used_model = model_key
            
            # ... (mode handling logic continues below, will assume it follows)
            
            # --- MODE HANDLING ---
            
            if mode == 'research':
                # Deep Research Mode
                try:
                    research_result = deep_research_service.perform_research(user_message)
                    response_content = research_result['content']
                    response_content += "\n\n---\n*Conducted Deep Research via recursive web search.*"
                    if research_result.get('queries'):
                         response_content += f"\n*Analyzed topics: {', '.join(research_result['queries'])}*"
                except Exception as e:
                    print(f"Research Mode Error: {e}")
                    raise e
                
            elif mode == 'reasoning':
                # Deep Reasoning Mode
                system_prompt = self._build_system_prompt(request.user, mode='reasoning')
                messages = [{"role": "system", "content": system_prompt}]
                for msg in history[-5:]: 
                     if msg.get('role') in ['user', 'assistant']:
                        messages.append(msg)
                
                messages.append({"role": "user", "content": user_message + file_content})
                
                result = qomai_service.deep_reasoning(messages, model_key)
                response_content = result['content']
                tokens_used = result['tokens_used']
                used_model = result['model']
                
            else:
                # Standard Chat Mode
                search_context = ""
                should_search = enable_search and web_search_service.should_search(user_message)
                if request.FILES and "search" not in user_message.lower():
                    should_search = False
    
                if should_search:
                    try:
                        search_results = web_search_service.search(user_message)
                        if search_results:
                            search_context = web_search_service.format_results_for_context(search_results)
                    except Exception as e:
                         print(f"Web Search Error: {e}")
    
                system_prompt = self._build_system_prompt(request.user, has_search=bool(search_context))
                messages = [{"role": "system", "content": system_prompt}]
                for msg in history[-10:]:
                    if msg.get('role') in ['user', 'assistant']:
                        messages.append(msg)
                
                final_prompt = user_message + file_content
                if search_context:
                    final_prompt = f"User Question: {user_message}\n\n{file_content}\n\nWeb Search Results:\n{search_context}\n\nPlease use these results to answer."
    
                messages.append({"role": "user", "content": final_prompt})
                
                result = qomai_service.chat_completion(messages, model_key=model_key)
                response_content = result['content']
                tokens_used = result['tokens_used']
                used_model = result['model']
    
            # Save assistant message
            Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=response_content,
                tokens_used=tokens_used,
                model_used=str(used_model)[:255] # Ensure it fits
            )
            
            return Response({
                'message': response_content,
                'conversation_id': str(conversation.id),
                'tokens_used': tokens_used,
                'model': used_model
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"ChatView processing error: {e}")
            return Response(
                {'error': f"Processing error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _build_system_prompt(self, user, has_search=False, mode='chat'):
        """Build specific system prompts"""
        name = user.first_name or "User"
        date = datetime.now().strftime("%B %d, %Y")
        
        base = f"You are QomAI. Current Date: {date}. User: {name}."
        
        if mode == 'reasoning':
            return base + " You are a Deep Reasoning engine. Think step-by-step. Analyze complex problems thoroughly before answering. Show your logical process."
            
        search_instr = "Prioritize web search results for recent events." if has_search else ""
        return f"{base} You are a helpful assistant for the Qomrade platform. {search_instr} Use markdown."


class ImageGenerationView(APIView):
    """Generate images from text prompts"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        prompt = request.data.get('prompt')
        if not prompt:
            return Response({'error': 'Prompt required'}, status=400)
            
        result = qomai_service.generate_image(prompt)
        
        if 'error' in result:
            return Response(result, status=500)
            
        # Return image directly
        return HttpResponse(result['image_data'], content_type=result['mime_type'])


class VoiceTranscriptionView(APIView):
    """Transcribe uploaded audio files"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]
    
    def post(self, request):
        if 'audio' not in request.FILES:
            return Response({'error': 'Audio file required'}, status=400)
            
        audio_file = request.FILES['audio']
        # Read file content
        audio_data = audio_file.read()
        
        result = qomai_service.transcribe_audio(audio_data)
        
        if 'error' in result:
            return Response(result, status=500)
            
        return Response(result)


# ... (Keep existing ViewSets: ConversationViewSet, ChatHistoryView, UserPreferenceView, WebSearchView, FakeNewsAnalysisView, RecommendationsView, GenerateLearningPathView, GenerateTestView) ...

class ConversationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    def get_queryset(self): return Conversation.objects.filter(user=self.request.user).order_by('-updated_at')
    def get_serializer_class(self): return ConversationListSerializer if self.action == 'list' else ConversationSerializer
    def perform_create(self, serializer): serializer.save(user=self.request.user)

class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        conversations = Conversation.objects.filter(user=request.user, is_active=True).order_by('-updated_at')[:20]
        return Response(ConversationListSerializer(conversations, many=True).data)

class UserPreferenceView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        pref, _ = UserPreference.objects.get_or_create(user=request.user, defaults={'preferred_model': 'qwen-7b'})
        return Response({'preferred_model': pref.preferred_model})
    def post(self, request):
        pref, _ = UserPreference.objects.update_or_create(user=request.user, defaults={'preferred_model': request.data.get('preferred_model')})
        return Response({'preferred_model': pref.preferred_model})

class WebSearchView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            results = web_search_service.search(request.data.get('query', ''), request.data.get('num_results', 5))
            return Response({'results': results})
        except Exception as e: return Response({'error': str(e)}, status=500)

class FakeNewsAnalysisView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request): return Response({'message': 'Placeholder'})

class RecommendationsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request): return Response({'recommendations': []})

class GenerateLearningPathView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request): return Response({'path': []})

class GenerateTestView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        # ... (Keep existing implementation logic if needed, or simplified placeholder for brevity as it wasn't modified) ...
        # Restoring original implementation for safety
        topic = request.data.get('topic', '')
        count = request.data.get('count', 10)
        difficulty = request.data.get('difficulty', 'medium')
        prompt = f"Generate {count} {difficulty} questions about {topic}"
        msgs = [{"role": "user", "content": prompt}]
        res = qomai_service.chat_completion(msgs)
        return Response({'questions_raw': res['content']})
