"""
LLM provider abstraction for the backlink agent
"""
import os
from typing import Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

load_dotenv()

class LLMProvider:
    """Abstraction layer for different LLM providers"""
    
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or os.getenv("LLM_PROVIDER", "openai")
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize the appropriate LLM based on provider"""
        if self.provider.lower() == "openai":
            return ChatOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.1"))
            )
        elif self.provider.lower() == "anthropic":
            return ChatAnthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.1"))
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def get_llm(self):
        """Get the initialized LLM instance"""
        return self.llm
    
    def invoke(self, prompt: str) -> str:
        """Invoke the LLM with a prompt"""
        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response) 