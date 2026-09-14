import os
from typing import TypedDict,Annotated
import operator
import psycopg
from langgraph.graph import START,END,StateGraph
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import (AIMessage,AnyMessage,HumanMessage,SystemMessage)
from langchain_groq import ChatGroq
# from tools.tavily import tavily_search
from mcp_tools.client import (tavily_search,aviation_mcp_call,get_airports,get_airlines,weather_mcp_search,forecast_mcp_search,extract_destination)
from dotenv import load_dotenv
import asyncio
load_dotenv()

# Intialize a LLM Model for calling

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="openai/gpt-oss-120b"
)
class TravelState(TypedDict):
    messages:Annotated[list[AnyMessage],operator.add]
    user_query:str
    flight_results:str
    hotel_results:str
    itinerary:str
    llm_calls:int
    weather_results:str

FLIGHT_AGENT_PROMPT = """
You are a travel flight expert.

User Query:
{query}

Airport Information:
{airport_data}

Airline Information:
{airline_data}

Generate:

1. Likely departure airport
2. Likely arrival airport
3. Airlines serving this route
4. Typical flight duration
5. Estimated airfare range
6. Peak season pricing warning
7. Booking advice

Return concise travel guidance.
"""

def flight_agent(state:TravelState):
    query = state["user_query"]
    airpots = asyncio.run(get_airports())
    airlines = asyncio.run(get_airlines())
    prompt = FLIGHT_AGENT_PROMPT.format(
        query=query,
        airport_data=str(airpots)[:3000],
        airline_data=str(airlines)[:3000]
    )
    response = llm.invoke([
        SystemMessage(content="You are an expert travel flight planner"),
        HumanMessage(content=prompt)
    ])
    flight_data = response.content
    return {
        "messages":[AIMessage(content=f"Here are the flight results for the query: {query}")],
        "flight_results":flight_data,
        "llm_calls": state.get("llm_calls", 0) + 1
    }

def hotel_agent(state:TravelState):
    query= f"Best hotel for {state['user_query']}"
    # tavily_search is the mcp tool provided by Tavily for searching hotels. It is an async function, so we need to run it in an event loop.
    hotel_result = asyncio.run(tavily_search(query))
    return {
        "hotel_results":hotel_result,
        "messages":[AIMessage(content=f"Hotel Information fetched")]
    }

def weather_agent(state: TravelState):

    city = extract_destination(state["user_query"])

    weather_data = asyncio.run(
        weather_mcp_search(city)
    )

    forecast_data = asyncio.run(
        forecast_mcp_search(city)
    )

    return {
        "weather_results": f"""
        Current Weather:
        {weather_data}

        Forecast:
        {forecast_data}
        """,
        "messages": [
            AIMessage(
                content="Weather information fetched"
            )
        ]
    }



def itinerary_agent(state:TravelState):
    prompt = f"""
    Create travel itinerary.

    User Query:
    {state['user_query']}

    Flight Results:
    {state['flight_results']}

    Hotel Results:
    {state['hotel_results']}

    Weather Results:
    {state['weather_results']}
    
    """
    reponse = llm.invoke([
        SystemMessage(content="You are an expert travel planner"),
        HumanMessage(content=prompt)
    ])
    return {
        "itinerary":reponse.content,
        "messages":[reponse],
        "llm_calls": state.get("llm_calls", 0) + 1
    }

# Final Reponse Agent
def final_agent(state: TravelState):

    final_prompt = f"""
    Generate final travel response.

    Flights:
    {state['flight_results']}

    Hotels:
    {state['hotel_results']}

    Itinerary:
    {state['itinerary']}
    """

    response = llm.invoke([
        HumanMessage(content=final_prompt)
    ])

    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


graph = StateGraph(TravelState)
graph.add_node("flight_agent",flight_agent)
graph.add_node("hotel_agent",hotel_agent)
graph.add_node("weather_agent",weather_agent)
graph.add_node("itinerary_agent",itinerary_agent);


graph.add_edge(START,"flight_agent")
graph.add_edge("flight_agent","hotel_agent")
graph.add_edge("hotel_agent","weather_agent")
graph.add_edge("weather_agent","itinerary_agent")
graph.add_edge("itinerary_agent",END)
# graph.add_edge("final_agent",END)

_conn = psycopg.connect(os.getenv("DATABASE_URL"), autocommit=True)
checkpointer = PostgresSaver(_conn)
checkpointer.setup()

app = graph.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    config = {
        "configurable": {
            "thread_id": "user_tejas"
        }
    }

    user_input = input("Enter travel request: ")

    result = app.invoke(
        {
            "messages": [
                HumanMessage(content=user_input)
            ],
            "user_query": user_input,
            "flight_results": "",
            "hotel_results": "",
            "weather_results": "",
            "itinerary": "",
            "llm_calls": 0
        },
        config=config
    )

    print("\nFINAL RESPONSE:\n")

    for msg in result["messages"]:
        print(msg.content)

