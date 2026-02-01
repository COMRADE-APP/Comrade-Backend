"""
QomAI Service - Qwen API through HuggingFace Router
Uses OpenAI-compatible API format with HuggingFace Router
"""
import os
import requests
from django.conf import settings


class QomAIService:
    """
    Service for interacting with Qwen model through HuggingFace Router
    Uses OpenAI-compatible chat completions API
    """
    
    # HuggingFace Router - OpenAI-compatible endpoint
    BASE_URL = "https://router.huggingface.co/v1"
    
    # Available Qwen models on HuggingFace Router
    QWEN_MODELS = {
        'qwen-0.5b': 'Qwen/Qwen2.5-0.5B-Instruct',
        'qwen-1.5b': 'Qwen/Qwen2.5-1.5B-Instruct',
        'qwen-3b': 'Qwen/Qwen2.5-3B-Instruct',
        'qwen-7b': 'Qwen/Qwen2.5-7B-Instruct',
        'qwen-14b': 'Qwen/Qwen2.5-14B-Instruct',
        'qwen-32b': 'Qwen/Qwen2.5-32B-Instruct',
        'qwen-72b': 'Qwen/Qwen2.5-72B-Instruct',
        'qwen-coder': 'Qwen/Qwen2.5-Coder-7B-Instruct',
    }
    
    DEFAULT_MODEL = 'qwen-7b'
    
    def __init__(self):
        self.hf_token = os.getenv('HF_TOKEN', '')
        model_key = os.getenv('QOMAI_MODEL', self.DEFAULT_MODEL)
        self.model = self.QWEN_MODELS.get(model_key, self.QWEN_MODELS[self.DEFAULT_MODEL])
        self.model_key = model_key
        
    def _get_headers(self):
        headers = {"Content-Type": "application/json"}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"
        return headers
    
    def chat_completion(self, messages, temperature=0.7, max_tokens=2048):
        """
        Send a chat completion request to Qwen via HuggingFace Router
        Uses OpenAI-compatible API format
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Creativity parameter (0-2)
            max_tokens: Maximum response length
            
        Returns:
            dict with 'content', 'tokens_used', 'model'
        """
        if not self.hf_token:
            # Fallback response when no API key is configured
            return {
                'content': self._get_fallback_response(messages),
                'tokens_used': 0,
                'model': 'fallback'
            }
        
        try:
            # OpenAI-compatible chat completions endpoint
            response = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers=self._get_headers(),
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse OpenAI-compatible response
                content = data['choices'][0]['message']['content']
                tokens_used = data.get('usage', {}).get('total_tokens', 0)
                
                return {
                    'content': content,
                    'tokens_used': tokens_used,
                    'model': f'qwen ({self.model_key})'
                }
            
            elif response.status_code == 503:
                # Model is loading
                return {
                    'content': "I'm warming up! The model is loading. Please try again in a moment.",
                    'tokens_used': 0,
                    'model': f'qwen ({self.model_key})'
                }
            
            elif response.status_code == 404:
                # Model not found - try alternative
                return {
                    'content': f"Model not available. Please check QOMAI_MODEL in .env. Error: {response.text}",
                    'tokens_used': 0,
                    'model': f'qwen ({self.model_key})'
                }
            
            else:
                error_msg = response.text
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', error_msg)
                except:
                    pass
                    
                return {
                    'content': f"I encountered an error: {error_msg}",
                    'tokens_used': 0,
                    'model': f'qwen ({self.model_key})'
                }
                
        except requests.exceptions.Timeout:
            return {
                'content': "I'm taking too long to respond. Please try again.",
                'tokens_used': 0,
                'model': f'qwen ({self.model_key})'
            }
        except Exception as e:
            return {
                'content': f"An error occurred: {str(e)}",
                'tokens_used': 0,
                'model': f'qwen ({self.model_key})'
            }
    
    def _get_fallback_response(self, messages):
        """
        Provide a helpful fallback response when API is not configured
        """
        user_message = messages[-1]['content'].lower() if messages else ''
        
        if 'help' in user_message or 'what can you do' in user_message:
            return """I'm QomAI, your platform assistant powered by Qwen! While my full AI capabilities require API configuration, I can still help you navigate the platform:

• **Rooms** - Collaborative spaces for discussions
• **Events** - Upcoming activities and gatherings
• **Articles** - Read and share knowledge
• **Research** - Academic and professional research
• **Learning Paths** - Structured skill development

To enable my full AI capabilities, please configure the HF_TOKEN in your environment variables.
Get your free token at: https://huggingface.co/settings/tokens"""
        
        elif 'event' in user_message:
            return "To find events, navigate to the Events page from the sidebar. You can filter by date, category, and location. Want me to explain how to create an event?"
        
        elif 'room' in user_message:
            return "Rooms are collaborative spaces for discussions. Visit the Rooms page to browse, join, or create new rooms. Each room can have its own events, resources, and member discussions."
        
        elif 'article' in user_message or 'research' in user_message:
            return "You can find articles and research in their respective sections. Use the search feature to find specific topics, or browse by category. You can also publish your own content!"
        
        elif 'payment' in user_message or 'money' in user_message:
            return "The Payments section lets you manage transactions, join payment groups, and track savings goals (piggy banks). Navigate to Payments from the sidebar for more options."
        
        else:
            return """Hello! I'm QomAI, your platform assistant powered by Qwen AI. 

Currently running in limited mode (API not configured). I can still provide basic navigation help:

• Ask about **events**, **rooms**, **articles**, or **payments**
• Say **"help"** to see what I can do

For full AI capabilities, configure HF_TOKEN in your .env file.
Get your free token at: https://huggingface.co/settings/tokens"""


# Singleton instance - keeping backward compatible name
deepseek_service = QomAIService()
