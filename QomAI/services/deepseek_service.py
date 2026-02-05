"""
QomAI Service - Multi-Model AI Service
Handles communication with various AI models via HuggingFace Inference API
Supports Text, Reasoning, Image Generation, and Audio Transcription
"""
import os
import requests
import json
from django.conf import settings


class QomAIService:
    """
    Unified Service for interacting with multiple AI models through HuggingFace
    """
    
    # HuggingFace Router - OpenAI-compatible endpoint
    BASE_URL = "https://router.huggingface.co/v1"
    API_URL_TEMPLATE = "https://api-inference.huggingface.co/models/{model}"
    
    # Available Models Configuration
    AVAILABLE_MODELS = {
        # --- Qwen Series (General Purpose) ---
        'qwen-0.5b': 'Qwen/Qwen2.5-0.5B-Instruct',
        'qwen-1.5b': 'Qwen/Qwen2.5-1.5B-Instruct',
        'qwen-3b': 'Qwen/Qwen2.5-3B-Instruct',
        'qwen-7b': 'Qwen/Qwen2.5-7B-Instruct',
        'qwen-14b': 'Qwen/Qwen2.5-14B-Instruct',
        'qwen-32b': 'Qwen/Qwen2.5-32B-Instruct',
        'qwen-72b': 'Qwen/Qwen2.5-72B-Instruct',
        'qwen-coder': 'Qwen/Qwen2.5-Coder-7B-Instruct',
        
        # --- DeepSeek Series (Reasoning & Code) ---
        'deepseek-v3': 'deepseek-ai/DeepSeek-V3',  # Check availability, fallback to 67b
        'deepseek-r1': 'deepseek-ai/DeepSeek-R1-Distill-Qwen-32B', # Reasoning focus
        
        # --- Llama Series (Meta) ---
        'llama-3-8b': 'meta-llama/Meta-Llama-3-8B-Instruct',
        'llama-3-70b': 'meta-llama/Meta-Llama-3-70B-Instruct',
        
        # --- GPT Class (Mistral/OpenAI alternatives) ---
        'gpt-mistral': 'mistralai/Mistral-7B-Instruct-v0.3',
        'gpt-mixtral': 'mistralai/Mixtral-8x7B-Instruct-v0.1',
        
        # --- Kimi / Yi (Chinese/English High Performance) ---
        'kimi-yi': '01-ai/Yi-1.5-34B-Chat',
    }
    
    # Multimodal Models
    IMAGE_MODEL = 'black-forest-labs/FLUX.1-dev' 
    AUDIO_MODEL = 'openai/whisper-large-v3-turbo'
    
    DEFAULT_MODEL = 'qwen-7b'
    
    def __init__(self):
        self.hf_token = os.getenv('HF_TOKEN', '')
        model_key = os.getenv('QOMAI_MODEL', self.DEFAULT_MODEL)
        # Default text model
        self.model = self.AVAILABLE_MODELS.get(model_key, self.AVAILABLE_MODELS[self.DEFAULT_MODEL])
        self.model_key = model_key
        
    def _get_headers(self):
        headers = {"Content-Type": "application/json"}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"
        return headers
    
    def _get_binary_headers(self):
        """Headers for binary data upload (audio/image)"""
        headers = {}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"
        return headers
    
    def chat_completion(self, messages, temperature=0.7, max_tokens=2048, model_key=None, stream=False):
        """
        Send a chat completion request
        """
        # Determine model to use
        selected_model = self.model
        if model_key and model_key in self.AVAILABLE_MODELS:
            selected_model = self.AVAILABLE_MODELS[model_key]
            
        if not self.hf_token:
            return self._get_fallback_response_dict(messages, model_key or self.model_key)
        
        try:
            # HuggingFace Router (OpenAI Compatible)
            response = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers=self._get_headers(),
                json={
                    "model": selected_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": stream
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                tokens_used = data.get('usage', {}).get('total_tokens', 0)
                return {
                    'content': content,
                    'tokens_used': tokens_used,
                    'model': selected_model
                }
            else:
                return self._handle_error(response, selected_model)
                
        except Exception as e:
            return {
                'content': f"An error occurred: {str(e)}",
                'tokens_used': 0,
                'model': selected_model
            }

    def generate_image(self, prompt, negative_prompt=""):
        """
        Generate an image using FLUX.1 or Stable Diffusion
        """
        if not self.hf_token:
            return {'error': 'HF_TOKEN required for image generation'}
            
        api_url = self.API_URL_TEMPLATE.format(model=self.IMAGE_MODEL)
        
        try:
            payload = {"inputs": prompt}
            if negative_prompt:
                payload["parameters"] = {"negative_prompt": negative_prompt}
                
            response = requests.post(api_url, headers=self._get_headers(), json=payload, timeout=60)
            
            if response.status_code == 200:
                return {'image_data': response.content, 'mime_type': 'image/jpeg'}
            else:
                return {'error': f"Image generation failed: {response.text}"}
        except Exception as e:
            return {'error': str(e)}

    def transcribe_audio(self, audio_data):
        """
        Transcribe audio using Whisper
        audio_data: bytes
        """
        if not self.hf_token:
            return {'text': 'HF_TOKEN required for transcription'}
            
        api_url = self.API_URL_TEMPLATE.format(model=self.AUDIO_MODEL)
        
        try:
            response = requests.post(
                api_url, 
                headers=self._get_binary_headers(), 
                data=audio_data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {'text': result.get('text', '')}
            else:
                return {'error': f"Transcription failed: {response.text}"}
        except Exception as e:
            return {'error': str(e)}

    def deep_reasoning(self, messages, model_key='deepseek-r1'):
        """
        Specialized method for Chain-of-Thought reasoning
        Preferably uses DeepSeek R1 or V3
        """
        # Inject CoT instructions if not already present
        system_msg = next((m for m in messages if m['role'] == 'system'), None)
        cot_instruction = "\n\nThink step-by-step. Break down the problem into logical components before answering. Provide a detailed chain of thought."
        
        if system_msg:
            system_msg['content'] += cot_instruction
        else:
            messages.insert(0, {"role": "system", "content": f"You are a helpful assistant.{cot_instruction}"})
            
        return self.chat_completion(messages, model_key=model_key, temperature=0.6)

    def _handle_error(self, response, model_name):
        """Handle API errors generically"""
        try:
            error_data = response.json()
            error_msg = error_data.get('error', {}).get('message', response.text)
        except:
            error_msg = response.text
            
        return {
            'content': f"Error with model {model_name}: {error_msg}",
            'tokens_used': 0,
            'model': model_name
        }

    def _get_fallback_response_dict(self, messages, model_key):
        """Dictionary wrapper for fallback"""
        # Reuse existing fallback logic logic but return dict
        content = self._get_fallback_response(messages)
        return {
            'content': content,
            'tokens_used': 0,
            'model': f'{model_key} (fallback)'
        }

    def _get_fallback_response(self, messages):
        """Legacy fallback string generator"""
        # ... (Keep original simple fallback logic) ...
        return "QomAI requires an HF_TOKEN to function. Please configure it in your .env file."

# Singleton instance
qomai_service = QomAIService()
# Backward compatibility
deepseek_service = qomai_service
