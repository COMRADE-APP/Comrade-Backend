"""
Voice Clone Service - High Fidelity TTS
Uses ElevenLabs (primary), OpenAI TTS, or Edge TTS (Free High-Quality Fallback)
"""
import os
import time
import threading
import requests
import asyncio
import edge_tts
from django.conf import settings

class VoiceCloneService:
    def __init__(self):
        self.elevenlabs_key = os.getenv('ELEVENLABS_API_KEY', '')
        self.openai_key = os.getenv('OPENAI_API_KEY', '')
        
        # Default to a deep, resonant voice ID that mimics Ezra Klein
        # Users can replace this with their specific cloned Voice ID
        self.elevenlabs_voice_id = os.getenv('ELEVENLABS_VOICE_ID', 'TxGEqnHWrfWFTfGW9XjX') # Default pre-made deep voice
        self.openai_voice = 'onyx' # Default deep male voice
        self.edge_voice = 'en-US-ChristopherNeural' # Free deep male voice
        
        # Caching for expensive operations
        self._voices_cache = None
        self._voices_cache_time = 0
        self._voices_cache_ttl = 300  # 5 minutes
        self._env_voices_cache = None
        self._env_voices_mtime = 0
        
        # Persistent event loop for Edge TTS (avoid creating/destroying per request)
        self._edge_loop = None
        self._edge_loop_lock = threading.Lock()

    def get_available_voices(self):
        """
        Fetches the user's available voices from ElevenLabs, OpenAI, and Edge TTS.
        Returns a list of formatted voice dictionaries.
        """
        self.elevenlabs_key = os.getenv('ELEVENLABS_API_KEY', '')
        self.openai_key = os.getenv('OPENAI_API_KEY', '')
        
        voices = []
        
        # 1. Add Free High-Quality Edge TTS voices (Always available, no API key needed)
        edge_voices = [
            {'id': 'en-US-ChristopherNeural', 'name': 'Free: Christopher (Deep Male)', 'provider': 'edgetts', 'preview_url': ''},
            {'id': 'en-US-GuyNeural', 'name': 'Free: Guy (Clear Male)', 'provider': 'edgetts', 'preview_url': ''},
            {'id': 'en-US-AriaNeural', 'name': 'Free: Aria (Clear Female)', 'provider': 'edgetts', 'preview_url': ''},
            {'id': 'en-US-JennyNeural', 'name': 'Free: Jenny (Natural Female)', 'provider': 'edgetts', 'preview_url': ''}
        ]
        voices.extend(edge_voices)
        
        # 2. Add standard OpenAI voices if key is present
        if self.openai_key:
            openai_voices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
            for v in openai_voices:
                voices.append({
                    'id': v,
                    'name': f"OpenAI {v.capitalize()}",
                    'provider': 'openai',
                    'preview_url': ''
                })

        # 3. Fetch ElevenLabs Voices (cached for 5 minutes to avoid hammering the API)
        if self.elevenlabs_key:
            try:
                now = time.time()
                if self._voices_cache is not None and (now - self._voices_cache_time) < self._voices_cache_ttl:
                    voices.extend(self._voices_cache)
                else:
                    response = requests.get(
                        "https://api.elevenlabs.io/v1/voices",
                        headers={"xi-api-key": self.elevenlabs_key},
                        timeout=10
                    )
                    if response.status_code == 200:
                        el_voices = response.json().get('voices', [])
                        cached_el = []
                        for v in el_voices:
                            # Mark custom cloned voices or library voices
                            category = "Cloned" if v.get('category') == 'cloned' else "ElevenLabs API"
                            cached_el.append({
                                'id': v['voice_id'],
                                'name': f"{v['name']} ({category})",
                                'provider': 'elevenlabs',
                                'preview_url': v.get('preview_url', '')
                            })
                        self._voices_cache = cached_el
                        self._voices_cache_time = now
                        voices.extend(cached_el)
            except Exception as e:
                print(f"Error fetching ElevenLabs voices: {e}")
                # Serve stale cache if available
                if self._voices_cache:
                    voices.extend(self._voices_cache)
                
        # 4. Inject explicitly defined custom Voice IDs from .env (cached by mtime)
        env_path = os.path.join(settings.BASE_DIR, '.env')
        if os.path.exists(env_path):
            try:
                current_mtime = os.path.getmtime(env_path)
                if self._env_voices_cache is not None and current_mtime == self._env_voices_mtime:
                    # .env hasn't changed, use cached result
                    for ev in self._env_voices_cache:
                        if not any(v['id'] == ev['id'] for v in voices):
                            voices.append(ev)
                else:
                    # .env changed or first load — read and cache
                    env_voices = []
                    with open(env_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, val = line.split('=', 1)
                                key, val = key.strip(), val.strip()
                                if key.endswith('_VOICE_ID') and key != 'ELEVENLABS_VOICE_ID':
                                    name = key.replace('_VOICE_ID', '').replace('_', ' ').title()
                                    env_voices.append({
                                        'id': val.strip('"\''),
                                        'name': f"{name} (ElevenLabs Custom env)",
                                        'provider': 'elevenlabs',
                                        'preview_url': ''
                                    })
                    self._env_voices_cache = env_voices
                    self._env_voices_mtime = current_mtime
                    for ev in env_voices:
                        if not any(v['id'] == ev['id'] for v in voices):
                            voices.append(ev)
            except Exception as e:
                print(f"Error parsing .env for custom voices: {e}")
                
        return voices

    def generate_speech(self, text, provider=None, voice_id=None):
        """
        Generate high fidelity speech audio bytes from text.
        Prioritizes user selection (provider & voice_id), falls back to default.
        """
        # Re-fetch keys in case the user just added them without restarting the server
        self.elevenlabs_key = os.getenv('ELEVENLABS_API_KEY', '')
        self.openai_key = os.getenv('OPENAI_API_KEY', '')
        
        # Override default voice if a specific one was requested
        if voice_id and provider == 'elevenlabs':
            self.elevenlabs_voice_id = voice_id
        elif voice_id and provider == 'openai':
            self.openai_voice = voice_id
        elif voice_id and provider == 'edgetts':
            self.edge_voice = voice_id
        else:
            self.elevenlabs_voice_id = os.getenv('ELEVENLABS_VOICE_ID', 'TxGEqnHWrfWFTfGW9XjX')
            self.openai_voice = 'onyx'
            self.edge_voice = 'en-US-ChristopherNeural'
        
        if provider == 'openai' and self.openai_key:
            return self._generate_openai(text)
        elif provider == 'elevenlabs' and self.elevenlabs_key:
            return self._generate_elevenlabs(text)
        elif provider == 'edgetts':
            return self._generate_edgetts(text)
            
        # Fallback logic if requested provider key is missing
        if self.elevenlabs_key:
            return self._generate_elevenlabs(text)
        elif self.openai_key:
            return self._generate_openai(text)
        else:
            return self._generate_edgetts(text) # Ultimate free fallback

    def _generate_elevenlabs(self, text):
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}/stream"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, stream=True)
            if response.status_code == 200:
                return {'audio_data': response.content, 'content_type': 'audio/mpeg'}
            else:
                try:
                     err_data = response.json()
                     msg = err_data.get('detail', {}).get('message', response.text)
                     return {'error': f"ElevenLabs API Error: {msg}"}
                except:
                     return {'error': f"ElevenLabs API Error: {response.text}"}
        except Exception as e:
            return {'error': str(e)}

    def _generate_openai(self, text):
        url = "https://api.openai.com/v1/audio/speech"
        
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "tts-1",
            "input": text,
            "voice": self.openai_voice,
            "response_format": "mp3"
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, stream=True)
            if response.status_code == 200:
                return {'audio_data': response.content, 'content_type': 'audio/mpeg'}
            else:
                return {'error': f"OpenAI API Error: {response.text}"}
        except Exception as e:
            return {'error': str(e)}

    async def _async_generate_edgetts(self, text):
        communicate = edge_tts.Communicate(text, self.edge_voice)
        chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        return b"".join(chunks)

    def _get_edge_loop(self):
        """Get or create a persistent event loop for Edge TTS on a background thread."""
        if self._edge_loop is None or self._edge_loop.is_closed():
            with self._edge_loop_lock:
                if self._edge_loop is None or self._edge_loop.is_closed():
                    self._edge_loop = asyncio.new_event_loop()
                    thread = threading.Thread(target=self._edge_loop.run_forever, daemon=True)
                    thread.start()
        return self._edge_loop

    def _generate_edgetts(self, text):
        try:
            loop = self._get_edge_loop()
            future = asyncio.run_coroutine_threadsafe(self._async_generate_edgetts(text), loop)
            audio_data = future.result(timeout=30)  # 30s safety timeout
            return {'audio_data': audio_data, 'content_type': 'audio/mpeg'}
        except Exception as e:
            return {'error': f"Edge TTS Error: {str(e)}"}

voice_clone_service = VoiceCloneService()
