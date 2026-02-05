"""
QomAI Deep Research Service
Conducts comprehensive research using recursive web search and LLM synthesis
"""
import concurrent.futures
from .deepseek_service import qomai_service
from .web_search_service import web_search_service

class DeepResearchService:
    """
    Service to perform deep research on a topic
    """
    
    def perform_research(self, query, depth=1, breadth=3):
        """
        Main entry point for deep research
        1. Generate search queries
        2. Execute searches
        3. Synthesize findings
        """
        # Step 1: Generate sub-queries
        sub_queries = self._generate_research_plan(query, breadth)
        
        # Step 2: Parallel Search
        all_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_query = {executor.submit(web_search_service.search, q, 3): q for q in sub_queries}
            for future in concurrent.futures.as_completed(future_to_query):
                q = future_to_query[future]
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as e:
                    print(f"Search failed for {q}: {e}")
        
        # Add original query search just in case
        all_results.extend(web_search_service.search(query, 5))
        
        # Step 3: Format & Synthesize
        context = web_search_service.format_results_for_context(all_results)
        return self._synthesize_report(query, context, sub_queries)

    def _generate_research_plan(self, query, count=3):
        """Use LLM to break down the query"""
        prompt = f"""I need to research the following topic deeply: "{query}"
        
        Generate {count} distinct, specific Google search queries that would help gather comprehensive information on this topic. 
        Focus on different aspects (e.g., history, current state, future outlook, controversy).
        
        Return ONLY the queries, one per line. Do not number them."""
        
        messages = [{"role": "user", "content": prompt}]
        response = qomai_service.chat_completion(messages, temperature=0.7)
        
        queries = [line.strip() for line in response['content'].split('\n') if line.strip()]
        return queries[:count] # Limit to requested breadth

    def _synthesize_report(self, query, context, sub_queries):
        """Synthesize a final report from gathered info"""
        prompt = f"""You are a Deep Research Agent. You have gathered information on the topic: "{query}".
        
        Research Strategy Used:
        {', '.join(sub_queries)}
        
        gathered_data:
        {context}
        
        Task: Write a comprehensive, well-structured research report.
        - Use professional tone.
        - Cite sources from the provided data.
        - Structure with Executive Summary, Key Findings, Details, and Conclusion.
        - Use Markdown for formatting.
        - Be objective and thorough."""
        
        messages = [{"role": "user", "content": prompt}]
        # Use a high-capacity model if possible, defaulting to main configured one
        response = qomai_service.chat_completion(messages, temperature=0.5, max_tokens=4000)
        
        return {
            'content': response['content'],
            'sources': context,     # Raw context for debug/reference
            'queries': sub_queries
        }

# Singleton
deep_research_service = DeepResearchService()
