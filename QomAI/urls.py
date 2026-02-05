"""
QomAI URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ChatView, ConversationViewSet, ChatHistoryView,
    FakeNewsAnalysisView, RecommendationsView,
    GenerateLearningPathView, GenerateTestView, 
    UserPreferenceView, WebSearchView,
    ImageGenerationView, VoiceTranscriptionView
)

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')

urlpatterns = [
    # Chat endpoint
    path('chat/', ChatView.as_view(), name='qomai-chat'),
    
    # History
    path('history/', ChatHistoryView.as_view(), name='qomai-history'),
    
    # User preferences (model selection, etc.)
    path('preferences/', UserPreferenceView.as_view(), name='qomai-preferences'),
    
    # Web search
    path('search/', WebSearchView.as_view(), name='qomai-search'),
    
    # Multimodal Enpoints
    path('generate/image/', ImageGenerationView.as_view(), name='generate-image'),
    path('transcribe/', VoiceTranscriptionView.as_view(), name='transcribe-voice'),
    
    # Analysis endpoints
    path('analyze/fake-news/', FakeNewsAnalysisView.as_view(), name='fake-news-analysis'),
    
    # Recommendations
    path('recommendations/', RecommendationsView.as_view(), name='recommendations'),
    
    # Content generation
    path('generate/learning-path/', GenerateLearningPathView.as_view(), name='generate-learning-path'),
    path('generate/test/', GenerateTestView.as_view(), name='generate-test'),
    
    # Router URLs
    path('', include(router.urls)),
]


