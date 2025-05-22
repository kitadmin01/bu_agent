"""
Configuration settings for the backlink agent
"""
import os
from dataclasses import dataclass
from typing import List

@dataclass
class AgentConfig:
    # Search queries for different niches
    WEB3_QUERIES: List[str] = None
    
    # Email template
    EMAIL_TEMPLATE: str = """
    Dear Team,
    
    I hope this email finds you well. I'm reaching out to propose a guest post for your website.
    
    I specialize in Web3 and blockchain marketing, and I believe I could provide valuable content
    for your audience. I have extensive experience in DeFi marketing strategies, NFT promotion,
    and blockchain technology adoption.
    
    Some topics I could cover include:
    - Web3 Marketing Best Practices
    - DeFi User Acquisition Strategies  
    - NFT Marketing and Community Building
    - Blockchain Technology Adoption in Traditional Business
    
    I've reviewed your guest post guidelines and would be happy to provide a detailed outline
    and samples of my previous work if you're interested.
    
    Thank you for your time and consideration.
    
    Best regards,
    Marketing Team
    AnalyticKit
    admin@analytickit.com
    """
    
    # Browser settings
    BROWSER_HEADLESS: bool = False
    BROWSER_TIMEOUT: int = 30
    
    # Rate limiting
    SEARCH_DELAY: int = 2
    SITE_ANALYSIS_DELAY: int = 3
    EMAIL_DELAY: int = 1
    
    def __post_init__(self):
        if self.WEB3_QUERIES is None:
            self.WEB3_QUERIES = [
                "web3 marketing",
                "blockchain marketing", 
                "DeFi marketing",
                "NFT marketing",
                "crypto marketing"
            ]

# Global config instance
config = AgentConfig() 