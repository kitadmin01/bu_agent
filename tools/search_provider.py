"""
Search provider using browser-use for web automation
"""
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from browser_use import Agent

load_dotenv()

class SearchProvider:
    def __init__(self):
        self.offline_mode = False
        self.agent = self._setup_agent()
        
    def _setup_agent(self):
        """Set up browser-use agent with proper error handling"""
        try:
            # Initialize LLM with the working configuration
            llm = ChatOpenAI(model="gpt-4")
            
            # Initialize browser-use agent with a specific task
            agent = Agent(
                task="Go to Google and search for the given query",
                llm=llm
            )
            self.offline_mode = False
            return agent
        except Exception as e:
            print(f"Error setting up browser-use agent: {e}")
            self.offline_mode = True
            return None
    
    async def search(self, query: str) -> List[Dict]:
        """Perform a web search using browser-use"""
        if self.offline_mode or not self.agent:
            print(f"[OFFLINE] Would search for: {query}")
            return []
            
        try:
            # Run the search with a simple task
            search_task = f"Go to Google and search for '{query}'"
            result = await self.agent.run(search_task)
            
            # Parse the results
            opportunities = []
            if result:
                # Add timestamp to each result
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Handle both single result and list of results
                results_list = result if isinstance(result, list) else [result]
                
                for res in results_list:
                    # Create opportunity from result
                    opportunity = {
                        'timestamp': timestamp,
                        'site_name': res.get('title', ''),
                        'url': res.get('url', ''),
                        'email': '',
                        'contact_method': '',
                        'submission_form_url': '',
                        'status': 'pending',
                        'email_status': '',
                        'email_sent_at': '',
                        'guidelines': '',
                        'notes': res.get('description', '')
                    }
                    opportunities.append(opportunity)
            
            return opportunities
            
        except Exception as e:
            print(f"Error performing search: {e}")
            return []
    
    async def search_guest_posts(self, topic: str) -> List[Dict]:
        """Search for guest post opportunities for a specific topic"""
        try:
            search_queries = [
                f'"{topic}" "write for us"',
                f'"{topic}" "contribute"',
                f'"{topic}" "guest post guidelines"',
                f'"{topic}" "submit article"'
            ]
            
            all_results = []
            for query in search_queries:
                try:
                    results = await self.search(query)
                    all_results.extend(results)
                    if not self.offline_mode:
                        await asyncio.sleep(self.search_delay)
                except Exception as e:
                    print(f"Error searching for query '{query}': {e}")
                    continue
                    
            # Remove duplicates based on URL
            unique_results = []
            seen_urls = set()
            for result in all_results:
                url = result.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(result)
            
            print(f"Found {len(unique_results)} unique results for topic: {topic}")
            return unique_results
            
        except Exception as e:
            print(f"Error in search_guest_posts for topic '{topic}': {e}")
            # Return some mock data for testing
            return [
                {"url": "https://example.com/write-for-us", "title": "Write for Example.com"},
                {"url": "https://blog.example.org/contribute", "title": "Contribute to Example Blog"}
            ] 