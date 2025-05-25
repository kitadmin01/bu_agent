"""
Backlink agent for finding and managing guest posting opportunities
"""
import asyncio
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()  # loads OPENAI_API_KEY from .env

from browser_use import Agent
from langchain_openai import ChatOpenAI
from tools.sheets_manager import GoogleSheetsManager
from utils.google_docs_manager import GoogleDocsManager

async def main():
    # Initialize your LLM (here using OpenAI via LangChain)
    llm = ChatOpenAI(model="gpt-4o")

    # Initialize storage managers
    sheets_manager = GoogleSheetsManager()
    docs_manager = GoogleDocsManager()

    # Create an agent that will search for guest posting opportunities
    agent = Agent(
        task="Go to Google and search for 'write for us' opportunities. For each result, extract the website URL, site name, and any contact information or submission guidelines.",
        llm=llm
    )

    # Run the agent and process results
    results = await agent.run()
    
    # Process and store results
    if isinstance(results, list):
        # Take top 10 results
        results = results[:10]
    else:
        results = [results]

    print(f"\nProcessing {len(results)} opportunities...")
    
    for result in results:
        if isinstance(result, dict):
            # Prepare opportunity data
            opportunity = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'site_name': result.get('site_name', ''),
                'url': result.get('url', ''),
                'email': result.get('email', ''),
                'contact_method': result.get('contact_method', ''),
                'submission_form_url': result.get('submission_form_url', ''),
                'status': 'pending',
                'email_status': '',
                'email_sent_at': '',
                'guidelines': result.get('guidelines', ''),
                'notes': ''
            }
            
            # Store in Google Sheets
            if sheets_manager.add_opportunity(opportunity):
                print(f"Added to Sheets: {opportunity['site_name']}")
            else:
                print(f"Failed to add to Sheets: {opportunity['site_name']}")
            
            # Store in Google Docs
            docs_result = docs_manager.insert_opportunity(opportunity)
            if docs_result['status'] == 'success':
                print(f"Added to Docs: {opportunity['site_name']}")
            else:
                print(f"Failed to add to Docs: {opportunity['site_name']}")

if __name__ == "__main__":
    asyncio.run(main()) 