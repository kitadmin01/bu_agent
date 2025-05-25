"""
LangGraph workflow for the backlink agent
"""
import asyncio
from typing import Dict, List, Any
from langgraph.graph import Graph, START, END
from backlink_agent import BacklinkAgent, BacklinkAgentState, GuestPostOpportunity

async def search_node(state: BacklinkAgentState) -> BacklinkAgentState:
    """Search for guest post opportunities"""
    agent = BacklinkAgent()
    try:
        results = await agent.search_google(state.query)
        state.search_results = results
        print(f"Search found {len(results)} results")
    except Exception as e:
        print(f"Error in search_node: {e}")
        state.search_results = []
    
    return state

async def analyze_node(state: BacklinkAgentState) -> BacklinkAgentState:
    """Analyze found websites for guest post opportunities"""
    agent = BacklinkAgent()
    opportunities = []
    
    for result in state.search_results:
        try:
            url = result.get('url', '')
            if url:
                opportunity = await agent.analyze_site(url)
                if opportunity.status != "error":
                    opportunities.append(opportunity)
                    # Update Google Sheets
                    agent.update_spreadsheet(opportunity.__dict__)
                    print(f"Analyzed site: {url}")
        except Exception as e:
            print(f"Error analyzing {result.get('url')}: {e}")
        
    state.opportunities = opportunities
    return state

async def email_node(state: BacklinkAgentState) -> BacklinkAgentState:
    """Send emails to identified opportunities"""
    agent = BacklinkAgent()
    emails_sent = []
    
    for opportunity in state.opportunities:
        try:
            result = await agent.send_outreach_email(opportunity.__dict__)
            emails_sent.append({
                "opportunity": opportunity.__dict__,
                "result": result
            })
            
            # Update opportunity status
            opportunity.email_status = result.get("status", "unknown")
            opportunity.email_sent_at = result.get("timestamp", "")
            
            # Update Google Sheets
            agent.update_spreadsheet({
                "url": opportunity.url,
                "email_status": result.get("status"),
                "email_sent_at": result.get("timestamp")
            })
            
            print(f"Email sent to {opportunity.site_name}: {result.get('status')}")
            
        except Exception as e:
            print(f"Error sending email to {opportunity.site_name}: {e}")
        
    state.emails_sent = emails_sent
    return state

async def check_replies_node(state: BacklinkAgentState) -> BacklinkAgentState:
    """Check for email replies to our outreach"""
    agent = BacklinkAgent()
    try:
        replies = await agent.check_for_email_replies()
        state.replies = replies
        print(f"Found {len(replies)} email replies")
    except Exception as e:
        print(f"Error checking for replies: {e}")
        state.replies = []
    
    return state

def create_workflow() -> Graph:
    """Create and compile the LangGraph workflow"""
    workflow = Graph()
    
    # Add nodes
    workflow.add_node("search", search_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("email", email_node)
    workflow.add_node("check_replies", check_replies_node)
    
    # Add edges
    workflow.add_edge(START, "search")
    workflow.add_edge("search", "analyze")
    workflow.add_edge("analyze", "email")
    workflow.add_edge("email", "check_replies")
    workflow.add_edge("check_replies", END)
    
    return workflow.compile()

async def run_workflow(queries: List[str]) -> None:
    """Run the workflow for multiple queries"""
    workflow = create_workflow()
    
    for query in queries:
        print(f"\nProcessing query: {query}")
        initial_state = BacklinkAgentState(query=query)
        
        try:
            # Run the workflow
            result = await workflow.ainvoke(initial_state)
            
            print(f"Found {len(result.opportunities)} opportunities")
            print(f"Sent {len(result.emails_sent)} emails")
            print(f"Received {len(result.replies)} replies")
        except Exception as e:
            print(f"Error running workflow for query '{query}': {e}")
        
        # Wait between queries to avoid rate limiting
        await asyncio.sleep(5) 