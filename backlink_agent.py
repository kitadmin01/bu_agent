import asyncio
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Tuple, Any, Callable
from datetime import datetime, timedelta
import random

import requests
from dotenv import load_dotenv
from browser_use import Agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool, BaseTool, ToolException
from langchain_core.messages import HumanMessage
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from pydantic import BaseModel, Field
from utils.llm_provider import LLMProvider
from tools.search_provider import SearchProvider
from tools.email_provider import EmailProvider
from utils.google_sheets_manager import GoogleSheetsManager

load_dotenv()

class GuestPostOpportunity(BaseModel):
    url: str
    site_name: str
    email: Optional[str] = None
    submission_form_url: Optional[str] = None
    guidelines: str = ""
    contact_method: str = ""
    status: str = "pending"
    notes: str = ""

class BacklinkAgentState(BaseModel):
    query: str = ""
    search_results: List[Dict] = Field(default_factory=list)
    opportunities: List[GuestPostOpportunity] = Field(default_factory=list)
    emails_sent: List[Dict] = Field(default_factory=list)
    current_opportunity: Optional[GuestPostOpportunity] = None
    replies: List[Dict] = Field(default_factory=list)

class BacklinkAgent:
    def __init__(self):
        self.llm_provider = LLMProvider()
        self.search_provider = SearchProvider()
        self.email_provider = EmailProvider()
        self.sheets_manager = GoogleSheetsManager()
        self.offline_mode = self.search_provider.offline_mode and self.email_provider.offline_mode
        
        # Initialize browser agent with LLM
        try:
            try:
                self.browser_agent = Agent(
                    task="Web automation for guest post discovery",
                    llm=self.llm_provider.get_llm()
                )
                self.browser_offline = False
            except AttributeError as ae:
                if "Screenshot" in str(ae):
                    print("Screenshot dependency issue detected, falling back to offline mode")
                    self.browser_agent = None
                    self.browser_offline = True
                else:
                    raise ae
        except Exception as e:
            print(f"Warning: Error initializing browser-use Agent with LLM provider: {e}")
            print("Using default OpenAI configuration...")
            try:
                # Fallback to direct OpenAI initialization
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if not openai_api_key:
                    raise ValueError("OPENAI_API_KEY environment variable is required")
                llm = ChatOpenAI(
                    api_key=openai_api_key,
                    model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
                )
                try:
                    self.browser_agent = Agent(
                        task="Web automation for guest post discovery",
                        llm=llm
                    )
                    self.browser_offline = False
                except AttributeError as ae:
                    if "Screenshot" in str(ae):
                        print("Screenshot dependency issue detected, falling back to offline mode")
                        self.browser_agent = None
                        self.browser_offline = True
                    else:
                        raise ae
            except Exception as e2:
                print(f"Warning: Direct OpenAI initialization also failed: {e2}")
                print("Operating in offline mode...")
                self.browser_agent = None
                self.browser_offline = True
        
        # Site analysis delay
        self.analysis_delay = int(os.getenv("SITE_ANALYSIS_DELAY", "3"))
        
        # Initialize tools
        self.search_google_tool = self._create_search_google_tool()
        self.analyze_site_tool = self._create_analyze_site_tool()
        self.send_outreach_email_tool = self._create_send_outreach_email_tool()
        self.update_spreadsheet_tool = self._create_update_spreadsheet_tool()
        self.check_for_email_replies_tool = self._create_check_for_email_replies_tool()

    def _create_search_google_tool(self) -> Tool:
        """Create a search_google tool"""
        return Tool(
            name="search_google",
            description="Search for guest post opportunities based on the given query.",
            func=self.search_google
        )
        
    def _create_analyze_site_tool(self) -> Tool:
        """Create an analyze_site tool"""
        return Tool(
            name="analyze_site",
            description="Analyze a website for guest post opportunities.",
            func=self.analyze_site
        )
        
    def _create_send_outreach_email_tool(self) -> Tool:
        """Create a send_outreach_email tool"""
        return Tool(
            name="send_outreach_email",
            description="Send a guest post outreach email to the given opportunity.",
            func=self.send_outreach_email
        )
        
    def _create_update_spreadsheet_tool(self) -> Tool:
        """Create an update_spreadsheet tool"""
        return Tool(
            name="update_spreadsheet",
            description="Update or add an entry in the Google Sheets tracking spreadsheet.",
            func=self.update_spreadsheet
        )
        
    def _create_check_for_email_replies_tool(self) -> Tool:
        """Create a check_for_email_replies tool"""
        return Tool(
            name="check_for_email_replies",
            description="Check for email replies to previously sent outreach emails.",
            func=self.check_for_email_replies
        )

    async def search_google(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for guest post opportunities based on the given query.
        
        Args:
            query: The search query to find guest post opportunities.
            
        Returns:
            A list of dictionaries containing search results.
        """
        try:
            print(f"Searching for: {query}")
            return await self.search_provider.search_guest_posts(query)
        except Exception as e:
            print(f"Error in search_google: {e}")
            # Return mock data on error
            return [
                {"url": "https://example.com/write-for-us", "title": "Example Write for Us Page"},
                {"url": "https://demo.org/guest-post", "title": "Guest Post - Demo.org"}
            ]

    async def analyze_site(self, url: str) -> GuestPostOpportunity:
        """
        Analyze a website for guest post opportunities.
        
        Args:
            url: The URL of the website to analyze.
            
        Returns:
            A GuestPostOpportunity object with the analysis results.
        """
        # Simplified handling of url parameter
        if not url:
            return GuestPostOpportunity(
                url="https://example.com",
                site_name="example.com",
                status="error",
                notes="No URL provided for analysis"
            )
            
        if self.browser_offline or not self.browser_agent:
            # Return mock data in offline mode
            print(f"[OFFLINE] Analyzing site: {url}")
            site_name = url.split("//")[-1].split("/")[0]
            has_email = random.choice([True, False])
            has_form = not has_email or random.choice([True, False])
            
            return GuestPostOpportunity(
                url=url,
                site_name=site_name,
                email=f"editor@{site_name}" if has_email else None,
                submission_form_url=f"https://{site_name}/submit" if has_form else None,
                guidelines="Please submit high-quality content related to our topics. Articles should be 1500-2000 words.",
                contact_method="email" if has_email else "form" if has_form else "",
                status="pending",
                notes="[MOCK DATA] This is offline test data"
            )
            
        try:
            # Use browser-use to visit and analyze the site
            analysis_result = await self.browser_agent.run(f"""
                Visit {url} and comprehensively analyze for guest post opportunities.
                
                Look for:
                1. "Write for us", "Contribute", "Guest post" pages/sections
                2. Contact forms specifically for submissions
                3. Email addresses for editorial/content submissions
                4. Guest post guidelines and requirements
                5. Examples of published guest posts
                
                Extract and return as a dictionary:
                - email: Contact email if found
                - form_url: Direct link to submission form if exists
                - guidelines: Full text of guidelines found
                - contact_method: "email", "form", or "both"
                - notes: Any additional relevant information
                - examples: URLs of example guest posts if found
            """)
            
            await asyncio.sleep(self.analysis_delay)
            
            # Parse the analysis result into a GuestPostOpportunity
            opportunity = GuestPostOpportunity(
                url=url,
                site_name=analysis_result.get("site_name") or url.split("//")[-1].split("/")[0],
                email=analysis_result.get("email"),
                submission_form_url=analysis_result.get("form_url"),
                guidelines=analysis_result.get("guidelines", ""),
                contact_method=analysis_result.get("contact_method", ""),
                notes=analysis_result.get("notes", "")
            )
            
            return opportunity
            
        except Exception as e:
            print(f"Site analysis error for {url}: {e}")
            return GuestPostOpportunity(
                url=url,
                site_name=url.split("//")[-1].split("/")[0],
                status="error",
                notes=f"Analysis failed: {str(e)}"
            )

    async def send_outreach_email(self, opportunity: Dict) -> Dict:
        """
        Send a guest post outreach email to the given opportunity.
        
        Args:
            opportunity: Information about the guest post opportunity.
            
        Returns:
            A dictionary with the result of the email sending operation.
        """
        # Convert dict to GuestPostOpportunity if needed
        if isinstance(opportunity, dict):
            try:
                opportunity = GuestPostOpportunity(**opportunity)
            except Exception as e:
                print(f"Error converting opportunity dict to object: {e}")
                return {"status": "error", "message": f"Invalid opportunity data: {str(e)}"}
        
        # Generate personalized email
        email_content = self.email_provider.generate_guest_post_email(
            opportunity.site_name, 
            opportunity.guidelines
        )
        
        # Send email using appropriate method
        result = await self.email_provider.send_email(
            to_email=opportunity.email,
            subject=email_content["subject"],
            message=email_content["message"],
            form_url=opportunity.submission_form_url
        )
        
        return result

    def update_spreadsheet(self, data: Dict) -> Dict:
        """
        Update or add an entry in the Google Sheets tracking spreadsheet.
        
        Args:
            data: The data to update or add.
            
        Returns:
            A dictionary with the result of the operation.
        """
        url = data.get('url')
        if not url:
            return {"status": "error", "message": "URL is required"}
            
        # Check if this is an update or a new entry
        if 'email_status' in data or 'email_sent_at' in data:
            # This is an update to an existing opportunity
            updates = {}
            
            if 'email_status' in data:
                updates['Email Status'] = data['email_status']
            if 'email_sent_at' in data:
                updates['Email Sent At'] = data['email_sent_at']
            
            # Check if we need to set a follow-up date
            if data.get('email_status') == 'success' and not data.get('follow_up_date'):
                # Set follow-up for 7 days later
                follow_up = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
                updates['Follow-up Date'] = follow_up
            
            # Add any other updates
            for key, value in data.items():
                if key not in ['url', 'email_status', 'email_sent_at'] and value:
                    # Convert to proper column name format
                    column_name = key.replace('_', ' ').title()
                    updates[column_name] = value
            
            return self.sheets_manager.update_opportunity(url, updates)
        else:
            # This is a new opportunity
            return self.sheets_manager.insert_opportunity(data)
            
    async def check_for_email_replies(self) -> List[Dict]:
        """
        Check for email replies to previously sent outreach emails.
        
        Returns:
            A list of dictionaries containing replies received.
        """
        if self.email_provider.offline_mode:
            print("[OFFLINE] Checking for email replies")
            # Generate mock replies in offline mode
            return [
                {
                    "id": "1",
                    "from": "editor@example.com",
                    "subject": "Re: Guest Post Proposal - Web3 Marketing Content",
                    "date": datetime.now().isoformat(),
                    "body": "Thanks for your proposal. Please send a detailed outline.",
                    "is_read": False
                }
            ]
            
        replies = await self.email_provider.check_for_replies()
        
        # Process each reply
        for reply in replies:
            # Try to match reply to an opportunity based on subject or content
            opportunities = self.sheets_manager.get_all_opportunities()
            
            for opportunity in opportunities:
                site_name = opportunity.get('Site Name', '')
                
                # Check if this reply is related to this opportunity
                if site_name and (
                    site_name.lower() in reply.get('subject', '').lower() or
                    site_name.lower() in reply.get('body', '').lower()
                ):
                    # Update the opportunity with the reply information
                    updates = {
                        'Response Summary': f"Reply received on {reply.get('date')} from {reply.get('from')}",
                        'Follow-up Date': ''  # Clear follow-up date as we got a response
                    }
                    
                    self.sheets_manager.update_opportunity(opportunity.get('URL'), updates)
                    
                    # Mark email as read
                    self.email_provider.mark_email_as_read(reply.get('id'))
        
        return replies

async def main():
    """Main function to run the backlink agent"""
    from workflow import run_workflow
    
    queries = [
        "web3 marketing",
        "blockchain marketing",
        "DeFi marketing",
        "NFT marketing"
    ]
    
    await run_workflow(queries)

if __name__ == "__main__":
    asyncio.run(main()) 