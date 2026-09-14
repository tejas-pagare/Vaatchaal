from pathlib import Path
import os

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from config.llm import get_llm
from utils.retry import with_async_retry, with_retry

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
AVIATIONSTACK_MCP_DIR = PROJECT_ROOT / "aviationstack-mcp"
AVIATIONSTACK_SERVER = AVIATIONSTACK_MCP_DIR / ".venv" / "bin" / "aviationstack-mcp"
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
WEATHER_SERVER = PROJECT_ROOT / "mcp_tools" / "custom_weather_mcp.py"
import sys
LOCAL_PYTHON = sys.executable

tavily_client = MultiServerMCPClient({
    "tavily": {
        "transport": "streamable_http",
        "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
    }
})

aviation_client = MultiServerMCPClient({
    "aviationstack": {
        "transport": "stdio",
        "command": str(AVIATIONSTACK_SERVER),
        "args": [],
        "cwd": str(AVIATIONSTACK_MCP_DIR),
        "env": {
            "AVIATION_STACK_API_KEY": AVIATIONSTACK_API_KEY
        }
    }
})

weather_client = MultiServerMCPClient({
    "weather": {
        "transport": "stdio",
        "command": str(LOCAL_PYTHON),
        "args": [str(WEATHER_SERVER)],
        "cwd": str(PROJECT_ROOT),
        "env": {
            **os.environ,
            "OPENWEATHER_API_KEY": OPENWEATHER_API_KEY
        }
    }
})

# async def main():
#     tools = await client.get_tools()
#     print("Available tools:")
#     for tool in tools:
#         print(tool.name)
    

# asyncio.run(main())

search_tool = None
aviation_tools = {}
async def initialize_aviation_tools():
    """Load Aviationstack MCP tools only."""
    global aviation_tools
    if aviation_tools:
        return

    aviation_loaded_tools = await aviation_client.get_tools()
    aviation_tools = {tool.name: tool for tool in aviation_loaded_tools}


async def initialize_tavily_tools():
    """Load Tavily MCP tools only."""
    global search_tool
    if search_tool is not None:
        return

    tavily_tools = await tavily_client.get_tools()
    search_tool = next(
        (
            tool for tool in tavily_tools
            if tool.name in {"tavily_search", "search"}
        ),
        None,
    )


async def intialize_mcp():
    """
    Initializes the MCP clients and retrieves cached tools."""
    await initialize_aviation_tools()
    await initialize_tavily_tools()

@with_async_retry()
async def aviation_mcp_call(tool_name:str,args:dict=None):
    """
    Calls the specified aviation tool from the MCP client.
    Args:
        tool_name (str): The name of the aviation tool to call.
        args (dict): The arguments to pass to the tool.
    Returns:
        The result from the aviation tool.
    """
    global aviation_tools
    if not aviation_tools:
        await initialize_aviation_tools()
    if tool_name not in aviation_tools:
        raise Exception(f"Tool {tool_name} not found in MCP tools.")
    result = await aviation_tools[tool_name].ainvoke(args or {})
    return result

async def get_airlines():
    """
    Retrieves the list of airlines using the aviationstack tool.
    Returns:
        The list of airlines from the aviationstack tool.
    """
    return await aviation_mcp_call("list_airlines", {})

async def get_airports():
    """
    Retrieves the list of airports using the aviationstack tool.
    Returns:
        The list of airports from the aviationstack tool.
    """
    return await aviation_mcp_call("list_airports", {})

@with_async_retry()
async def tavily_search(query: str):
    """
    Performs a search using the Tavily search tool.
    Args:
        query (str): The search query.
    Returns:
        The search results from the Tavily search tool.
    """
    global search_tool
    if search_tool is None:
        await initialize_tavily_tools()
    if search_tool is None:
        raise Exception("Search tool not found in MCP tools.")
    result = await search_tool.ainvoke({
        "query": query
    })
    return result

weather_tool = None
forecast_tool = None


async def initialize_weather_tools():

    global weather_tool, forecast_tool

    if weather_tool is not None:
        return

    tools = await weather_client.get_tools()

    weather_tool = next(
        t for t in tools
        if t.name == "get_current_weather"
    )

    forecast_tool = next(
        t for t in tools
        if t.name == "get_forecast"
    )


@with_async_retry()
async def weather_mcp_search(city: str):

    await initialize_weather_tools()

    return await weather_tool.ainvoke(
        {
            "city": city
        }
    )


@with_async_retry()
async def forecast_mcp_search(city: str):

    await initialize_weather_tools()

    return await forecast_tool.ainvoke(
        {
            "city": city
        }
    )

llm = get_llm()

@with_retry()
def extract_destination(query: str):

    prompt = f"""
    Extract only the destination city or country.

    Query:
    {query}

    Return only destination name.
    """

    response = llm.invoke(prompt)

    return response.content.strip()
