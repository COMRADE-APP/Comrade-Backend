"""
Web Search Service for QomAI
Provides internet search capabilities using DuckDuckGo
"""
import requests
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus


class WebSearchService:
    """
    Service for searching the web using DuckDuckGo
    No API key required - uses DuckDuckGo's instant answer API
    """
    
    # DuckDuckGo endpoints
    DDG_INSTANT_API = "https://api.duckduckgo.com/"
    DDG_HTML_SEARCH = "https://html.duckduckgo.com/html/"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Search the web using DuckDuckGo
        
        Args:
            query: Search query string
            num_results: Maximum number of results to return
            
        Returns:
            List of search results with title, url, and snippet
        """
        results = []
        
        # Try instant answer API first (for quick facts)
        instant = self._get_instant_answer(query)
        if instant:
            results.append(instant)
        
        # Get web search results
        web_results = self._search_web(query, num_results)
        results.extend(web_results)
        
        return results[:num_results]
    
    def _get_instant_answer(self, query: str) -> Optional[Dict]:
        """Get instant answer from DuckDuckGo"""
        try:
            response = self.session.get(
                self.DDG_INSTANT_API,
                params={
                    'q': query,
                    'format': 'json',
                    'no_html': 1,
                    'skip_disambig': 1
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for abstract (Wikipedia-style answer)
                if data.get('Abstract'):
                    return {
                        'title': data.get('Heading', 'Instant Answer'),
                        'url': data.get('AbstractURL', ''),
                        'snippet': data.get('Abstract', ''),
                        'source': data.get('AbstractSource', 'DuckDuckGo'),
                        'type': 'instant'
                    }
                
                # Check for answer (direct answer)
                if data.get('Answer'):
                    return {
                        'title': 'Direct Answer',
                        'url': '',
                        'snippet': data.get('Answer', ''),
                        'source': 'DuckDuckGo',
                        'type': 'answer'
                    }
                    
        except Exception as e:
            print(f"Instant answer error: {e}")
        
        return None
    
    def _search_web(self, query: str, num_results: int) -> List[Dict]:
        """Search web using DuckDuckGo HTML"""
        results = []
        
        try:
            response = self.session.post(
                self.DDG_HTML_SEARCH,
                data={'q': query, 'b': ''},
                timeout=15
            )
            
            if response.status_code == 200:
                # Parse HTML results
                html = response.text
                
                # Extract results using regex (simple parsing)
                # Look for result links and snippets
                result_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
                snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>([^<]*(?:<[^>]*>[^<]*)*)</a>'
                
                links = re.findall(result_pattern, html)
                snippets = re.findall(snippet_pattern, html)
                
                for i, (url, title) in enumerate(links[:num_results]):
                    snippet = snippets[i] if i < len(snippets) else ''
                    # Clean snippet
                    snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                    
                    if url and title:
                        results.append({
                            'title': title.strip(),
                            'url': url,
                            'snippet': snippet,
                            'source': 'Web',
                            'type': 'web'
                        })
                        
        except Exception as e:
            print(f"Web search error: {e}")
        
        return results
    
    def format_results_for_context(self, results: List[Dict]) -> str:
        """Format search results for AI context"""
        if not results:
            return "No search results found."
        
        formatted = "**Web Search Results:**\n\n"
        
        for i, result in enumerate(results, 1):
            formatted += f"{i}. **{result['title']}**\n"
            if result['url']:
                formatted += f"   Source: {result['url']}\n"
            formatted += f"   {result['snippet']}\n\n"
        
        return formatted
    
    def should_search(self, message: str) -> bool:
        """
        Determine if a message needs web search
        Checks for indicators that user wants current/recent information
        """
        message_lower = message.lower()
        
        # Keywords that suggest need for current info
        current_keywords = [
            'latest', 'recent', 'current', 'today', 'now',
            'this year', 'this month', 'this week',
            '2024', '2025', '2026',  # Years after training cutoff
            'news', 'update', 'what happened',
            'search', 'look up', 'find out',
            'who is the current', 'who won',
            'stock price', 'weather', 'score',
            'breaking', 'just announced', 'recently'
        ]
        
        # Check if any keyword is present
        for keyword in current_keywords:
            if keyword in message_lower:
                return True
        
        # Check for questions about recent events
        recent_patterns = [
            r'what (is|are) .* (now|today|currently)',
            r'(latest|newest|most recent) .* (news|update|version)',
            r'did .* (win|happen|occur|die|resign)',
            r'when did .* (last|recently)',
            r'how much (is|does|did) .* (cost|worth)',
        ]
        
        for pattern in recent_patterns:
            if re.search(pattern, message_lower):
                return True
        
        return False


# Singleton instance
web_search_service = WebSearchService()
