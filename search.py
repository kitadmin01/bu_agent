import asyncio
from dotenv import load_dotenv
load_dotenv()  # loads OPENAI_API_KEY from .env

from browser_use import Agent
from langchain_openai import ChatOpenAI

async def main():
    # Initialize your LLM (here using OpenAI via LangChain)
    llm = ChatOpenAI(model="gpt-4o")  

    # Create an agent that will open Google and search for "ai news"
    agent = Agent(
        task="Go to https://www.google.com, search for \"ai news\", and return the page title.", 
        llm=llm
    )

    # Run the agent and print its output
    result = await agent.run()
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
