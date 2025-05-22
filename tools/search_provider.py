"""
Search provider abstraction for the backlink agent
"""
import os
import asyncio
import json
import random
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class SearchProvider:
    """Abstraction layer for different search providers"""
    
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or os.getenv("SEARCH_PROVIDER", "google")
        self.offline_mode = True
        self.agent = self._setup_agent()
        self.max_results = int(os.getenv("SEARCH_MAX_RESULTS", "5"))
        self.search_delay = int(os.getenv("SEARCH_DELAY", "2"))
        
        # Load mock data for offline mode
        self.mock_data = {
            "write for us": [
                {"url": "https://web3marketing.com/write-for-us", "title": "Write for Web3 Marketing"},
                {"url": "https://defiblogs.io/contribute", "title": "Contribute to DeFi Blogs"},
                {"url": "https://nftmarketing.com/guest-post", "title": "Guest Post Guidelines - NFT Marketing"}
            ],
            "contribute": [
                {"url": "https://blockchaintoday.com/contribute", "title": "Contribute to Blockchain Today"},
                {"url": "https://cryptoinsight.com/guest-writers", "title": "Become a Guest Writer"}
            ],
            "guest post guidelines": [
                {"url": "https://web3daily.com/guidelines", "title": "Guest Post Guidelines - Web3 Daily"},
                {"url": "https://decentral.news/write-for-us", "title": "Write for Decentral News"}
            ],
            "submit article": [
                {"url": "https://tokenomics.blog/submit", "title": "Submit Your Article - Tokenomics Blog"},
                {"url": "https://cryptomarketing.guide/submit-content", "title": "Submit Content - Crypto Marketing Guide"}
            ]
        }
    
    def _setup_agent(self):
        """Set up browser-use agent with proper error handling"""
        try:
            # Import and initialize browser-use
            try:
                from browser_use import Agent
                from langchain_openai import ChatOpenAI
                from utils.llm_provider import LLMProvider
                
                # Debug: Check the selenium-screenshot package
                try:
                    import selenium_screenshot
                    print(f"selenium_screenshot version: {selenium_screenshot.__version__}")
                    print(f"selenium_screenshot dir: {dir(selenium_screenshot)}")
                    
                    # Check if Screenshot is in the module
                    if hasattr(selenium_screenshot, 'Screenshot'):
                        print("Screenshot class found in selenium_screenshot module")
                        print(f"Screenshot attributes: {dir(selenium_screenshot.Screenshot)}")
                    else:
                        print("Warning: No Screenshot class in selenium_screenshot module")
                except Exception as se:
                    print(f"Error inspecting selenium_screenshot: {se}")
                
                # Try using LLMProvider
                try:
                    llm_provider = LLMProvider()
                    # Don't use browser-use Agent if Screenshot issues
                    try:
                        agent = Agent(
                            task="Web search automation",
                            llm=llm_provider.get_llm()
                        )
                        self.offline_mode = False
                        return agent
                    except AttributeError as ae:
                        if "Screenshot" in str(ae):
                            print(f"Screenshot dependency issue details: {ae}")
                            print("Screenshot dependency issue detected, using offline mode")
                            self.offline_mode = True
                            return None
                        else:
                            raise ae
                except Exception as e:
                    print(f"Warning: Error initializing browser-use Agent with LLM provider: {e}")
                    print("Trying direct OpenAI initialization...")
                    
                    # Try direct OpenAI initialization
                    try:
                        openai_api_key = os.getenv("OPENAI_API_KEY")
                        if not openai_api_key:
                            raise ValueError("OPENAI_API_KEY environment variable is required")
                        
                        llm = ChatOpenAI(
                            api_key=openai_api_key,
                            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
                        )
                        # Don't use browser-use Agent if Screenshot issues
                        try:
                            agent = Agent(
                                task="Web search automation",
                                llm=llm
                            )
                            self.offline_mode = False
                            return agent
                        except AttributeError as ae:
                            if "Screenshot" in str(ae):
                                print("Screenshot dependency issue detected, using offline mode")
                                self.offline_mode = True
                                return None
                            else:
                                raise ae
                    except Exception as e2:
                        print(f"Warning: Direct OpenAI initialization also failed: {e2}")
                        print("Falling back to offline mode...")
                        self.offline_mode = True
                        return None
                    
            except ImportError as e:
                print(f"Warning: browser-use library not available: {e}")
                print("Using offline mode with mock data.")
                self.offline_mode = True
                return None
        except Exception as e:
            print(f"Warning: Unexpected error initializing browser-use: {e}")
            print("Using offline mode with mock data.")
            self.offline_mode = True
            return None
    
    async def search(self, query: str) -> List[Dict]:
        """Search using the configured provider"""
        if self.offline_mode:
            return self._offline_search(query)
            
        if self.provider.lower() == "google":
            return await self._search_google(query)
        elif self.provider.lower() == "bing":
            return await self._search_bing(query)
        else:
            print(f"Unsupported search provider: {self.provider}, using offline mode")
            return self._offline_search(query)
    
    def _offline_search(self, query: str) -> List[Dict]:
        """Return mock data when in offline mode"""
        print(f"[OFFLINE] Searching for: {query}")
        
        # Find matching mock data
        for key in self.mock_data:
            if key in query.lower():
                # Add some randomness
                results = self.mock_data.get(key, [])
                random.shuffle(results)
                return results[:self.max_results]
        
        # If no match, return a random sample
        all_results = []
        for results in self.mock_data.values():
            all_results.extend(results)
        
        random.shuffle(all_results)
        return all_results[:self.max_results]
    
    async def _search_google(self, query: str) -> List[Dict]:
        """Search Google using browser automation"""
        if self.offline_mode or not self.agent:
            return self._offline_search(query)
            
        try:
            search_result = await self.agent.run(
                f"Search Google for: {query} and extract the top {self.max_results} URLs with titles and descriptions"
            )
            await asyncio.sleep(self.search_delay)
            
            # Ensure we return a list of dictionaries
            if isinstance(search_result, list):
                return search_result
            elif isinstance(search_result, dict):
                return [search_result]
            else:
                # Parse string response if needed
                return self._parse_search_results(search_result)
                
        except Exception as e:
            print(f"Google search error: {e}")
            print("Falling back to offline mode for this search")
            return self._offline_search(query)
    
    async def _search_bing(self, query: str) -> List[Dict]:
        """Search Bing using browser automation"""
        if self.offline_mode or not self.agent:
            return self._offline_search(query)
            
        try:
            search_result = await self.agent.run(
                f"Search Bing for: {query} and extract the top {self.max_results} URLs with titles and descriptions"
            )
            await asyncio.sleep(self.search_delay)
            return search_result if isinstance(search_result, list) else [search_result]
        except Exception as e:
            print(f"Bing search error: {e}")
            print("Falling back to offline mode for this search")
            return self._offline_search(query)
    
    def _parse_search_results(self, results) -> List[Dict]:
        """Parse search results into standardized format"""
        try:
            if isinstance(results, str):
                # Try to parse as JSON
                try:
                    parsed = json.loads(results)
                    if isinstance(parsed, list):
                        return parsed
                    elif isinstance(parsed, dict):
                        return [parsed]
                except json.JSONDecodeError:
                    pass
                    
            # Return a default value
            print("Could not parse search results, returning empty list")
            return []
        except Exception as e:
            print(f"Error parsing search results: {e}")
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