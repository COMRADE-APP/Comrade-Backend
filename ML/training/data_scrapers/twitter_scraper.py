"""
Twitter/X Data Scraper for Fake News Training Data

This script collects tweets for training the fake news detection model.
Uses the Twitter API v2 to collect tweets about trending topics.

Requirements:
- Twitter Developer Account with API access
- Bearer token in environment variable TWITTER_BEARER_TOKEN
"""

import os
import json
import time
from datetime import datetime, timedelta
import requests
from typing import List, Dict, Optional


class TwitterScraper:
    """
    Scraper for collecting tweets using Twitter API v2
    """
    
    BASE_URL = "https://api.twitter.com/2"
    
    def __init__(self):
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN', '')
        
    def _get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }
    
    def search_tweets(
        self, 
        query: str, 
        max_results: int = 100,
        start_time: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for recent tweets matching a query.
        
        Args:
            query: Search query (supports Twitter search operators)
            max_results: Maximum number of tweets to return (10-100)
            start_time: ISO 8601 timestamp for start of search window
            
        Returns:
            List of tweet dictionaries
        """
        if not self.bearer_token:
            print("Warning: TWITTER_BEARER_TOKEN not set. Using mock data.")
            return self._get_mock_data()
        
        endpoint = f"{self.BASE_URL}/tweets/search/recent"
        
        params = {
            "query": query,
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,author_id,public_metrics,source",
            "expansions": "author_id",
            "user.fields": "name,username,verified"
        }
        
        if start_time:
            params["start_time"] = start_time
        
        try:
            response = requests.get(
                endpoint,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            else:
                print(f"Error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"Request failed: {e}")
            return []
    
    def collect_news_tweets(
        self,
        keywords: List[str],
        per_keyword: int = 50
    ) -> List[Dict]:
        """
        Collect tweets about news topics.
        
        Args:
            keywords: List of keywords to search for
            per_keyword: Number of tweets per keyword
            
        Returns:
            List of collected tweets
        """
        all_tweets = []
        
        for keyword in keywords:
            print(f"Collecting tweets for: {keyword}")
            
            # Search for tweets
            tweets = self.search_tweets(
                query=f"{keyword} -is:retweet lang:en",
                max_results=per_keyword
            )
            
            # Add source label
            for tweet in tweets:
                tweet['search_keyword'] = keyword
                tweet['collected_at'] = datetime.utcnow().isoformat()
            
            all_tweets.extend(tweets)
            
            # Rate limiting
            time.sleep(1)
        
        return all_tweets
    
    def _get_mock_data(self) -> List[Dict]:
        """Return mock data for development without API access"""
        return [
            {
                "id": "mock_1",
                "text": "Breaking: Scientists discover new renewable energy source",
                "author_id": "user_1",
                "created_at": datetime.utcnow().isoformat(),
                "public_metrics": {
                    "retweet_count": 100,
                    "like_count": 500,
                    "reply_count": 50
                }
            },
            {
                "id": "mock_2", 
                "text": "ALERT: You won't believe what happens next! Click here!",
                "author_id": "user_2",
                "created_at": datetime.utcnow().isoformat(),
                "public_metrics": {
                    "retweet_count": 1000,
                    "like_count": 50,
                    "reply_count": 200
                }
            }
        ]
    
    def save_to_json(self, tweets: List[Dict], filepath: str):
        """Save collected tweets to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(tweets, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(tweets)} tweets to {filepath}")
    
    def load_from_json(self, filepath: str) -> List[Dict]:
        """Load tweets from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)


class FakeNewsDataCollector:
    """
    Collects and labels data for fake news detection training.
    Combines Twitter data with Kaggle datasets.
    """
    
    # Keywords often associated with misinformation
    SUSPICIOUS_KEYWORDS = [
        "breaking",
        "you won't believe",
        "scientists hate",
        "one weird trick",
        "media won't tell you",
        "secret revealed",
        "shocking truth"
    ]
    
    # Trusted news source domains
    TRUSTED_SOURCES = [
        "reuters.com",
        "apnews.com",
        "bbc.com",
        "npr.org",
        "nytimes.com"
    ]
    
    def __init__(self):
        self.twitter = TwitterScraper()
    
    def collect_training_data(self, output_dir: str = "../data"):
        """
        Collect tweets for training data.
        
        Uses different queries to get balanced data:
        - General news topics
        - Potentially misleading content
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Collect news tweets
        news_keywords = [
            "climate change",
            "election",
            "economy",
            "health",
            "technology",
            "science",
            "politics"
        ]
        
        news_tweets = self.twitter.collect_news_tweets(news_keywords, per_keyword=50)
        self.twitter.save_to_json(news_tweets, f"{output_dir}/news_tweets.json")
        
        # Collect potentially unreliable tweets
        sketchy_keywords = [
            "conspiracy",
            "mainstream media lies",
            "they don't want you to know",
            "wake up sheeple"
        ]
        
        sketchy_tweets = self.twitter.collect_news_tweets(sketchy_keywords, per_keyword=50)
        self.twitter.save_to_json(sketchy_tweets, f"{output_dir}/sketchy_tweets.json")
        
        print(f"\nCollection complete!")
        print(f"News tweets: {len(news_tweets)}")
        print(f"Suspicious tweets: {len(sketchy_tweets)}")
        
        return news_tweets, sketchy_tweets
    
    def extract_features(self, tweet: Dict) -> Dict:
        """Extract features for fake news detection"""
        text = tweet.get('text', '')
        metrics = tweet.get('public_metrics', {})
        
        features = {
            'text': text,
            'text_length': len(text),
            'has_link': 'http' in text.lower(),
            'exclamation_count': text.count('!'),
            'question_count': text.count('?'),
            'all_caps_ratio': sum(1 for c in text if c.isupper()) / max(len(text), 1),
            'retweet_count': metrics.get('retweet_count', 0),
            'like_count': metrics.get('like_count', 0),
            'reply_count': metrics.get('reply_count', 0),
            'engagement_ratio': (
                metrics.get('reply_count', 0) / 
                max(metrics.get('retweet_count', 1), 1)
            ),
            'suspicious_keyword_count': sum(
                1 for kw in self.SUSPICIOUS_KEYWORDS 
                if kw.lower() in text.lower()
            )
        }
        
        return features


if __name__ == "__main__":
    # Run collection
    collector = FakeNewsDataCollector()
    
    print("Starting data collection...")
    print("Note: Set TWITTER_BEARER_TOKEN in .env for real data")
    
    collector.collect_training_data()
