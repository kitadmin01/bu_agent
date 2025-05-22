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
        # Call the method directly
        results = await agent.search_google(state.query)
        state.search_results = results
        print(f"Search found {len(results)} results")
    except Exception as e:
        print(f"Error in search_node: {e}")
        # Return some fallback results if search fails
        state.search_results = [
            {"url": "https://example.com/write-for-us", "title": "Example Write for Us Page"},
            {"url": "https://demo.org/guest-post", "title": "Guest Post Guidelines"}
        ]
    
    return state

async def analyze_node(state: BacklinkAgentState) -> BacklinkAgentState:
    """Analyze found websites for guest post opportunities"""
    agent = BacklinkAgent()
    opportunities = []
    
    for result in state.search_results:
        try:
            url = result.get('url', '')
            if url:
                # Make sure url is a string
                url_str = url if isinstance(url, str) else str(url)
                opportunity = await agent.analyze_site(url_str)
                opportunities.append(opportunity)
                
                # Update Google Sheets with found opportunity
                opp_dict = opportunity.dict() if hasattr(opportunity, 'dict') else opportunity
                agent.update_spreadsheet(opp_dict)
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
        if opportunity.status == "error":
            continue
            
        try:
            # Make sure we pass proper dictionary
            opp_dict = opportunity.dict() if hasattr(opportunity, 'dict') else dict(opportunity)
            # Call the send_outreach_email method directly
            result = await agent.send_outreach_email(opp_dict)
            
            emails_sent.append({
                "opportunity": opp_dict,
                "result": result
            })
            
            # Update opportunity status
            opportunity.status = result.get("status", "unknown")
            
            # Update Google Sheets with email status
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
        # Call the check_for_email_replies method directly
        replies = await agent.check_for_email_replies()
        
        # Store the replies in the state
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