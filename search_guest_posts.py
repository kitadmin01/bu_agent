import asyncio
from dotenv import load_dotenv
from typing import List, Dict
from datetime import datetime
import uuid
import json
load_dotenv()  # loads OPENAI_API_KEY from .env

from browser_use import Agent
from langchain_openai import ChatOpenAI
from tools.email_provider import EmailProvider
from tools.sheets_manager import GoogleSheetsManager

async def analyze_site(agent: Agent, url: str) -> Dict:
    """Analyze a website for guest posting opportunities"""
    analyze_task = f"""Go to {url} and analyze it for guest posting opportunities. Look for:
    1. Site name/title
    2. Contact information or email
    3. Submission form URL if present
    4. Guest post guidelines
    5. Content requirements
    
    Return the findings as a structured response with these fields:
    - site_name: The name of the website
    - email: Contact email if found
    - contact_method: How to contact (email, form, etc.)
    - submission_form_url: URL of submission form if found
    - guidelines: Any guest post guidelines found"""
    
    result = await agent.run(analyze_task)
    return result

async def send_outreach_email(email_provider: EmailProvider, opportunity: Dict) -> Dict:
    """Send outreach email for a guest posting opportunity"""
    email_data = email_provider.generate_guest_post_email(
        site_name=opportunity['site_name'],
        guidelines=opportunity['guidelines']
    )
    
    # Try sending via form first if available
    if opportunity['submission_form_url']:
        result = await email_provider.send_email(
            to_email=opportunity['email'],
            subject=email_data['subject'],
            message=email_data['message'],
            form_url=opportunity['submission_form_url']
        )
    # Otherwise try email
    elif opportunity['email']:
        result = await email_provider.send_email(
            to_email=opportunity['email'],
            subject=email_data['subject'],
            message=email_data['message']
        )
    else:
        result = {
            "status": "no_contact",
            "message": "No contact method available"
        }
    
    return result

async def main():
    # Initialize your LLM (here using OpenAI via LangChain)
    llm = ChatOpenAI(model="gpt-4o")  

    # Initialize email provider and sheets manager
    email_provider = EmailProvider()
    sheets_manager = GoogleSheetsManager()

    # Create an agent that will search for guest posting opportunities
    agent = Agent(
        task="""Go to https://www.google.com and perform the following steps:
        1. Wait for the page to load completely
        2. Find the search input box
        3. Type 'web3 marketing write for us'
        4. Press Enter or click the search button
        5. Wait for search results to load
        6. Extract the top 5 results and return them in this exact JSON format:
        {
          "search_results": [
            {
              "title": "Result Title",
              "url": "https://result-url.com"
            }
          ]
        }""", 
        llm=llm
    )

    # Run the search
    print("\nSearching for guest posting opportunities...")
    try:
        search_results = await agent.run()
        print("\nSearch Results:")
        print(search_results)

        # Extract results from AgentHistoryList
        opportunities = []
        if hasattr(search_results, 'all_results'):
            print("\nProcessing search results...")
            # Find the last result with is_done=True
            final_result = None
            for result in search_results.all_results:
                print(f"Checking result: is_done={result.is_done}, has_content={bool(result.extracted_content)}")
                if result.is_done and result.extracted_content:
                    final_result = result  # keep updating to get the last one
            if final_result:
                print("Found final result!")
                try:
                    print(f"\nFinal result content: {final_result.extracted_content}")
                    # Parse the JSON from the final result
                    data = json.loads(final_result.extracted_content)
                    print(f"Parsed data: {data}")
                    if 'search_results' in data:
                        for item in data['search_results']:
                            print(f"Processing item: {item}")
                            opportunity = {
                                'id': str(uuid.uuid4()),
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'site_name': item.get('title', ''),
                                'url': item.get('url', ''),
                                'email': '',
                                'contact_method': '',
                                'submission_form_url': '',
                                'status': 'pending',
                                'email_status': '',
                                'email_sent_at': '',
                                'guidelines': '',
                                'notes': ''
                            }
                            opportunities.append(opportunity)
                            print(f"Found opportunity: {opportunity['site_name']}")
                except Exception as e:
                    print(f"Error parsing search results: {e}")
                    import traceback
                    print(f"Traceback: {traceback.format_exc()}")
            else:
                print("No final result found with is_done=True")

        if not opportunities:
            print("No opportunities found to save")
            return

        # Analyze each opportunity
        print("\nAnalyzing opportunities...")
        for opp in opportunities:
            try:
                print(f"\nAnalyzing: {opp['url']}")
                analysis = await analyze_site(agent, opp['url'])
                
                # Update opportunity with analysis results
                opp['email'] = analysis.get('email', '')
                opp['contact_method'] = analysis.get('contact_method', '')
                opp['submission_form_url'] = analysis.get('submission_form_url', '')
                opp['guidelines'] = analysis.get('guidelines', '')
                
                print(f"Analysis complete for: {opp['site_name']}")
            except Exception as e:
                print(f"Error analyzing {opp['url']}: {e}")

        # Save opportunities to Google Sheets
        print("\nSaving opportunities to Google Sheets...")
        for opp in opportunities:
            try:
                print(f"\nAttempting to save: {opp['site_name']}")
                success = sheets_manager.add_opportunity(opp)
                if success:
                    print(f"Successfully saved to sheets: {opp['site_name']}")
                else:
                    print(f"Failed to save to sheets: {opp['site_name']}")
            except Exception as e:
                print(f"Error saving to sheets: {e}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")

        # Send outreach emails
        print("\nSending outreach emails...")
        for opp in opportunities:
            try:
                email_result = await send_outreach_email(email_provider, opp)
                
                # Update opportunity with email status
                opp['email_status'] = email_result['status']
                opp['email_sent_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Update Google Sheets
                sheets_manager.update_opportunity(opp)
                
                print(f"Email sent to {opp['site_name']}: {email_result['status']}")
            except Exception as e:
                print(f"Error sending email to {opp['site_name']}: {e}")

        # Print final summary
        print("\nFinal Summary:")
        for opp in opportunities:
            print(f"\nSite: {opp['site_name']}")
            print(f"URL: {opp['url']}")
            print(f"Contact: {opp['contact_method']}")
            print(f"Email Status: {opp['email_status']}")
            if opp['email']:
                print(f"Email: {opp['email']}")
            if opp['submission_form_url']:
                print(f"Form: {opp['submission_form_url']}")
            if opp['guidelines']:
                print(f"Guidelines: {opp['guidelines'][:200]}...")

    except Exception as e:
        print(f"Error during search: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(main()) 
