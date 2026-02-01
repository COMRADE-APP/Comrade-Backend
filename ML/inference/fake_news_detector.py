"""
Fake News Detector Inference Module

This module provides production-ready inference for the fake news detection model.
Uses HuggingFace Inference API when local model is not available.
"""

import os
import requests
from typing import Dict, Optional
import json


class FakeNewsDetector:
    """
    Fake news detection using transfer learning.
    Supports local model or HuggingFace Inference API fallback.
    """
    
    # Free models on HuggingFace that can detect fake news
    HF_MODELS = {
        'default': 'hamzab/roberta-fake-news-classification',
        'distilbert': 'jy46604790/Fake-News-Bert-Detect',
        'sbert': 'GonzaloA/fake_news'
    }
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the detector.
        
        Args:
            model_path: Path to local model, or None to use HuggingFace API
        """
        self.model_path = model_path
        self.hf_token = os.getenv('HF_TOKEN', '')
        self.hf_model = self.HF_MODELS['default']
        self.local_model = None
        self.local_tokenizer = None
        
        if model_path and os.path.exists(model_path):
            self._load_local_model()
    
    def _load_local_model(self):
        """Load locally trained model"""
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            
            self.local_tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.local_model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
            print(f"Loaded local model from {self.model_path}")
        except Exception as e:
            print(f"Failed to load local model: {e}")
    
    def predict(self, text: str) -> Dict:
        """
        Predict if text is fake news.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with prediction results
        """
        if self.local_model:
            return self._predict_local(text)
        else:
            return self._predict_huggingface(text)
    
    def _predict_local(self, text: str) -> Dict:
        """Run prediction using local model"""
        import torch
        
        inputs = self.local_tokenizer(
            text,
            return_tensors='pt',
            truncation=True,
            max_length=512
        )
        
        with torch.no_grad():
            outputs = self.local_model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)
            prediction = torch.argmax(probs, dim=1).item()
            confidence = probs[0][prediction].item()
        
        return {
            'is_fake': prediction == 1,
            'confidence': confidence,
            'label': 'fake' if prediction == 1 else 'real',
            'source': 'local_model',
            'probabilities': {
                'real': float(probs[0][0]),
                'fake': float(probs[0][1])
            }
        }
    
    def _predict_huggingface(self, text: str) -> Dict:
        """Run prediction using HuggingFace Inference API"""
        api_url = f"https://api-inference.huggingface.co/models/{self.hf_model}"
        
        headers = {}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"
        
        try:
            response = requests.post(
                api_url,
                headers=headers,
                json={"inputs": text[:1000]},  # Limit text length
                timeout=30
            )
            
            if response.status_code == 200:
                results = response.json()
                
                # Parse HuggingFace response
                if isinstance(results, list) and len(results) > 0:
                    if isinstance(results[0], list):
                        results = results[0]
                    
                    # Find best prediction
                    best = max(results, key=lambda x: x.get('score', 0))
                    label = best.get('label', '').lower()
                    score = best.get('score', 0)
                    
                    is_fake = 'fake' in label or 'false' in label or label == '1'
                    
                    return {
                        'is_fake': is_fake,
                        'confidence': score,
                        'label': 'fake' if is_fake else 'real',
                        'source': 'huggingface_api',
                        'raw_response': results
                    }
            
            # Fallback for errors
            return self._rule_based_detection(text)
            
        except Exception as e:
            print(f"HuggingFace API error: {e}")
            return self._rule_based_detection(text)
    
    def _rule_based_detection(self, text: str) -> Dict:
        """
        Simple rule-based detection as fallback.
        Not accurate but provides some functionality without API.
        """
        text_lower = text.lower()
        
        # Suspicious patterns
        suspicious_patterns = [
            "you won't believe",
            "shocking truth",
            "they don't want you to know",
            "mainstream media",
            "wake up",
            "secret revealed",
            "breaking!!",
            "share before deleted"
        ]
        
        # Count suspicious patterns
        suspicious_count = sum(1 for p in suspicious_patterns if p in text_lower)
        
        # All caps ratio
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        
        # Exclamation marks
        exclaim_ratio = text.count('!') / max(len(text), 1)
        
        # Simple scoring
        score = (suspicious_count * 0.2) + (caps_ratio * 0.3) + (exclaim_ratio * 50)
        is_fake = score > 0.3
        
        return {
            'is_fake': is_fake,
            'confidence': min(score, 0.99),
            'label': 'fake' if is_fake else 'real',
            'source': 'rule_based',
            'message': 'Using rule-based fallback. Results may not be accurate.'
        }
    
    def batch_predict(self, texts: list) -> list:
        """Predict for multiple texts"""
        return [self.predict(text) for text in texts]


# Singleton instance for easy import
detector = FakeNewsDetector()


def analyze_content(text: str) -> Dict:
    """Convenience function for quick analysis"""
    return detector.predict(text)


if __name__ == "__main__":
    # Quick test
    test_texts = [
        "Scientists at MIT have developed a new solar panel that is 40% more efficient than current models.",
        "BREAKING!!! You won't BELIEVE what the government is hiding from you! Share before they delete this!!!",
        "The Federal Reserve announced a 0.25% interest rate increase today, citing inflation concerns."
    ]
    
    print("Fake News Detection Test\n" + "="*50)
    
    for text in test_texts:
        result = analyze_content(text)
        print(f"\nText: {text[:80]}...")
        print(f"Prediction: {result['label'].upper()}")
        print(f"Confidence: {result['confidence']:.2%}")
        print(f"Source: {result['source']}")
