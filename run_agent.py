#!/usr/bin/env python3
"""
Main entry point for the backlink agent
"""
import os
import asyncio
from dotenv import load_dotenv
from backlink_agent import BacklinkAgent
from workflow import run_workflow

load_dotenv()

async def main():
    """Run the backlink agent"""
    
    # Define search queries
    queries = [
        "web3 marketing",
        "blockchain marketing",
        "DeFi marketing",
        "NFT marketing"
    ]
    
    # Get query from environment if available
    custom_query = os.getenv("SEARCH_QUERY")
    if custom_query:
        queries = [custom_query]

    # Run the workflow
    await run_workflow(queries)

if __name__ == "__main__":
    asyncio.run(main()) 