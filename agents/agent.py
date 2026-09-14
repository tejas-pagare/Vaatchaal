import asyncio
import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt

from config.llm import get_llm
from mcp_tools.client import weather_mcp_search, forecast_mcp_search, get_airlines, get_airports, tavily_search
from state.state import TravelState
from utils.retry import with_retry
from utils.image_service import fetch_place_image

logger = logging.getLogger(__name__)

llm = get_llm()

@with_retry()
def _llm_text(system: str, prompt: str) -> str:
    response = llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=prompt),
        ]
    )
    return response.content

def _json_from_llm(text: str) -> dict:
    print("\n========== RAW LLM RESPONSE ==========")
    print(text)
    print("======================================\n")

    start = text.index("{")
    end = text.rindex("}") + 1

    json_text = text[start:end]

    print("\n========== EXTRACTED JSON ==========")
    print(json_text)
    print("====================================\n")

    return json.loads(json_text)


# with guardrail
def supervisor_agent(state: TravelState):
    query = state["user_query"]
            
    # INPUT GUARDRAIL
    guardrail_prompt = f"""
    Determine whether the following request is a valid travel planning request.

    Return only JSON in this format:

    {{
        "allowed": true,
        "reason": ""
    }}

    User request:
    {query}
    """

    guardrail_raw = _llm_text(
        "You are an input validation guardrail. Return strict JSON only.",
        guardrail_prompt,
    )

    print("\n========== GUARDRAIL RAW RESPONSE ==========")
    print(guardrail_raw)
    print("============================================\n")

    guardrail_result = _json_from_llm(guardrail_raw)

    print("\n========== GUARDRAIL PARSED RESPONSE ==========")
    print(json.dumps(guardrail_result, indent=2))
    print("================================================\n")

    if not guardrail_result.get("allowed", False):
        reason = guardrail_result.get(
            "reason",
            "Request rejected by input guardrail."
        )

        return {
            "selected_agents": [],
            "trip_constraints": {},
            "supervisor_reasoning": reason,
            "final_response": reason,
            "messages": [
                AIMessage(content=f"Guardrail blocked request: {reason}")
            ],
            "llm_calls": state.get("llm_calls", 0) + 1,
            "agent_trace": [{
                "agent": "supervisor",
                "tools": ["Input Guardrail (LLM)"],
                "summary": f"Request blocked: {reason}",
            }],
        }


    # supervisor logic is starting from here:

    existing_constraints = state.get("trip_constraints", {})
    existing_itinerary = state.get("itinerary", "")

    prompt = f"""
You are the supervisor of a real-world multi-agent travel planning system.

Decide which specialist agents are needed for this user request.
If this is a follow-up or refinement to an existing trip (e.g. "make it cheaper", "add a day", "focus on food"), merge and update the existing trip constraints.

Existing constraints (if any):
{json.dumps(existing_constraints, indent=2)}

Existing draft itinerary (if any):
{existing_itinerary[:1200] if existing_itinerary else "None"}

Available agents:
- flight_agent: use when flights, airports, airlines, routes, or airfare guidance are needed or changed
- hotel_agent: use when hotels, stays, neighborhoods, or accommodation are needed or changed
- weather_agent: use when weather, climate, season, packing, or forecast is useful
- budget_agent: use when budget, affordability, cost, or price constraints are mentioned or updated
- itinerary_agent: almost always needed to produce or update the travel plan

Return only JSON with this schema:
{{
  "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"],
  "trip_constraints": {{
    "destination": "Destination name",
    "origin": "Departure city if mentioned",
    "duration": "Trip duration (e.g. 5 days)",
    "budget": "Budget if mentioned",
    "travel_style": "Style/vibe",
    "special_preferences": []
  }},
  "reasoning": "Brief explanation of routing decision"
}}

User request:
{query}
"""

    raw = _llm_text(
        "You route work to specialist agents and handle trip refinements. Return strict JSON only.",
        prompt,
    )

    print("\n========== RAW LLM RESPONSE ==========")
    print(raw)
    print("======================================\n")

    parsed = _json_from_llm(raw)
   
    #parsed = json.loads(raw)
    
    print("\n========== PARSED JSON ==========")
    print(json.dumps(parsed, indent=2))
    print("=================================\n")
    
    '''
    At first glance they look the same, but they're not:

    raw → string returned by the LLM
    parsed → Python dictionary created from that string

    If you really want to demonstrate the difference, add:

    print(type(raw))
    print(type(parsed))
    Output:

    <class 'str'>
    <class 'dict'>
    Yes, you can get output from a string, but it's much harder and less reliable.
    '''
    
    selected = parsed["selected_agents"]    

    return {
        "selected_agents": selected,
        "trip_constraints": parsed["trip_constraints"],
        "supervisor_reasoning": parsed["reasoning"],
        "messages": [AIMessage(content="Supervisor created the agent plan.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
        "agent_trace": [{
            "agent": "supervisor",
            "tools": ["Input Guardrail (LLM)", "Agent Router (LLM)"],
            "summary": f"Selected agents: {', '.join(selected)}",
        }],
    }






# without guardrail

# def supervisor_agent(state: TravelState):
#     query = state["user_query"]
#     prompt = f"""
# You are the supervisor of a real-world multi-agent travel planning system.

# Decide which specialist agents are needed for this user request.

# Available agents:
# - flight_agent: use when flights, airports, airlines, routes, or airfare guidance are needed
# - hotel_agent: use when hotels, stays, neighborhoods, or accommodation are needed
# - weather_agent: use when weather, climate, season, packing, or forecast is useful
# - budget_agent: use when budget, affordability, cost, or price constraints are mentioned
# - itinerary_agent: almost always needed to produce the travel plan

# Return only JSON with this schema:
# {{
#   "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"],
#   "trip_constraints": {{
#     "destination": "",
#     "origin": "",
#     "duration": "",
#     "budget": "",
#     "travel_style": "",
#     "special_preferences": []
#   }},
#   "reasoning": ""
# }}

# User request:
# {query}
# """
    
#     raw = _llm_text(
#         "You route work to specialist agents. Return strict JSON only.",
#         prompt,
#     )

#     print("\n========== RAW LLM RESPONSE ==========")
#     print(raw)
#     print("======================================\n")

#     parsed = _json_from_llm(raw)
#     print("\n========== PARSED JSON ==========")
#     print(json.dumps(parsed, indent=2))
#     print("=================================\n")

#     print(type(raw))
#     print(type(parsed))

#     selected = parsed["selected_agents"]       

#     return {
#         "selected_agents": selected,
#         "trip_constraints": parsed["trip_constraints"],
#         "supervisor_reasoning": parsed["reasoning"],
#         "messages": [AIMessage(content="Supervisor created the agent plan.")],
#         "llm_calls": state.get("llm_calls", 0) + 1,
#     }



def flight_agent(state: TravelState):
    query = state["user_query"]
    constraints = state["trip_constraints"]
    destination = constraints["destination"]

    try:
        print("\n========== FLIGHT AGENT INPUT ==========")
        print("Query:", query)
        print("Constraints:", constraints)
        print("========================================\n")

        airports = asyncio.run(get_airports())
        airlines = asyncio.run(get_airlines())

        print("\n========== AIRPORT MCP DATA ==========")
        print(airports)
        print("======================================\n")

        print("\n========== AIRLINE MCP DATA ==========")
        print(airlines)
        print("======================================\n")

        prompt = f"""
Create flight guidance for this trip.

User request:
{query}

Trip constraints:
{constraints}

Airport MCP data:
{str(airports)[:3000]}

Airline MCP data:
{str(airlines)[:3000]}

Include likely departure/arrival airports, relevant airlines,
estimated duration, fare range, peak season warning,
and booking advice.
"""

        result = _llm_text(
            "You are a flight planning specialist.",
            prompt,
        )

        print("\n========== FLIGHT AGENT OUTPUT ==========")
        print(result)
        print("=========================================\n")

        return {
            "flight_results": result,
            "messages": [AIMessage(content="Flight agent completed.")],
            "llm_calls": state.get("llm_calls", 0) + 1,
            "agent_trace": [{
                "agent": "flight_agent",
                "tools": ["get_airports (MCP)", "get_airlines (MCP)", "LLM call"],
                "summary": f"Flight guidance for: {destination}",
            }],
        }
    except Exception as exc:
        logger.error("Flight agent failed: %s", exc)
        return {
            "flight_results": "Flight data unavailable — Aviationstack MCP unreachable.",
            "messages": [AIMessage(content="Flight agent failed.")],
            "agent_trace": [{
                "agent": "flight_agent",
                "tools": ["get_airports (MCP)", "get_airlines (MCP)"],
                "summary": f"Error: {exc}",
                "error": True,
            }],
        }




def hotel_agent(state: TravelState):
    query = f"Best hotels and areas to stay for: {state['user_query']}"

    try:
        print("\n========== HOTEL AGENT INPUT ==========")
        print(query)
        print("=======================================\n")

        result = asyncio.run(tavily_search(query))

        print("\n========== HOTEL SEARCH RESULT ==========")
        print(result)
        print("=========================================\n")

        return {
            "hotel_results": str(result),
            "messages": [AIMessage(content="Hotel agent completed.")],
            "agent_trace": [{
                "agent": "hotel_agent",
                "tools": ["tavily_search (MCP)"],
                "summary": f"Hotel search for: {state['user_query']}",
            }],
        }
    except Exception as exc:
        logger.error("Hotel agent failed: %s", exc)
        return {
            "hotel_results": "Hotel data unavailable — Tavily search unreachable.",
            "messages": [AIMessage(content="Hotel agent failed.")],
            "agent_trace": [{
                "agent": "hotel_agent",
                "tools": ["tavily_search (MCP)"],
                "summary": f"Error: {exc}",
                "error": True,
            }],
        }


def weather_agent(state: TravelState):
    constraints = state["trip_constraints"]
    city = constraints["destination"]

    try:
        print("\n========== WEATHER AGENT INPUT ==========")
        print("City:", city)
        print("=========================================\n")

        weather_data = asyncio.run(weather_mcp_search(city))
        forecast_data = asyncio.run(forecast_mcp_search(city))

        print("\n========== CURRENT WEATHER ==========")
        print(weather_data)
        print("=====================================\n")

        print("\n========== WEATHER FORECAST ==========")
        print(forecast_data)
        print("======================================\n")

        result = f"""
Current weather:
{weather_data}

Forecast:
{forecast_data}
"""

        print("\n========== WEATHER AGENT OUTPUT ==========")
        print(result)
        print("==========================================\n")

        return {
            "weather_results": result,
            "messages": [AIMessage(content="Weather agent completed.")],
            "agent_trace": [{
                "agent": "weather_agent",
                "tools": ["get_current_weather (MCP)", "get_forecast (MCP)"],
                "summary": f"Weather data for: {city}",
            }],
        }
    except Exception as exc:
        logger.error("Weather agent failed: %s", exc)
        return {
            "weather_results": "Weather data unavailable — OpenWeather MCP unreachable.",
            "messages": [AIMessage(content="Weather agent failed.")],
            "agent_trace": [{
                "agent": "weather_agent",
                "tools": ["get_current_weather (MCP)", "get_forecast (MCP)"],
                "summary": f"Error: {exc}",
                "error": True,
            }],
        }



def budget_agent(state: TravelState):

    try:
        print("\n========== BUDGET AGENT INPUT ==========")
        print("Trip Constraints:")
        print(state.get("trip_constraints"))
        print("\nFlight Results:")
        print(state.get("flight_results"))
        print("\nHotel Results:")
        print(state.get("hotel_results"))
        print("\nWeather Results:")
        print(state.get("weather_results"))
        print("=========================================\n")

        prompt = f"""
Analyze whether this trip plan is realistic for the user's budget.

User request:
{state['user_query']}

Constraints:
{state.get('trip_constraints', {})}

Flight results:
{state.get('flight_results', '')}

Hotel results:
{state.get('hotel_results', '')}

Weather results:
{state.get('weather_results', '')}

Return a concise budget assessment with:
1. estimated cost categories
2. risk areas
3. money-saving suggestions
4. whether the plan seems feasible
"""

        result = _llm_text(
            "You are a practical travel budget analyst.",
            prompt,
        )

        print("\n========== BUDGET AGENT OUTPUT ==========")
        print(result)
        print("=========================================\n")

        return {
            "budget_results": result,
            "messages": [AIMessage(content="Budget agent completed.")],
            "llm_calls": state.get("llm_calls", 0) + 1,
            "agent_trace": [{
                "agent": "budget_agent",
                "tools": ["LLM call"],
                "summary": "Budget feasibility analysis",
            }],
        }
    except Exception as exc:
        logger.error("Budget agent failed: %s", exc)
        return {
            "budget_results": "Budget analysis unavailable — LLM call failed.",
            "messages": [AIMessage(content="Budget agent failed.")],
            "agent_trace": [{
                "agent": "budget_agent",
                "tools": ["LLM call"],
                "summary": f"Error: {exc}",
                "error": True,
            }],
        }



def itinerary_agent(state: TravelState):

    print("\n========== ITINERARY AGENT INPUT ==========")
    print("Trip Constraints:")
    print(state.get("trip_constraints"))

    print("\nFlight Results:")
    print(state.get("flight_results"))

    print("\nHotel Results:")
    print(state.get("hotel_results"))

    print("\nWeather Results:")
    print(state.get("weather_results"))

    print("\nBudget Results:")
    print(state.get("budget_results"))
    print("===========================================\n")

    prompt = f"""
Create a clear draft travel itinerary.

User request:
{state['user_query']}

Trip constraints:
{state.get('trip_constraints', {})}

Flight results:
{state.get('flight_results', '')}

Hotel results:
{state.get('hotel_results', '')}

Weather results:
{state.get('weather_results', '')}

Budget results:
{state.get('budget_results', '')}

Make the output structured, practical, and ready for human review.
"""

    result = _llm_text(
        "You are an expert itinerary planner.",
        prompt,
    )

    print("\n========== ITINERARY OUTPUT ==========")
    print(result)
    print("======================================\n")

    approval_request = f"""
Please review this draft travel plan.

{result}

Reply with approval or feedback.
"""

    async def _enrich_itinerary():
        destination = state.get("trip_constraints", {}).get("destination", "") or state.get("user_query", "")
        dest_image = await fetch_place_image(destination, "travel")
        
        # Extract structured days with landmark names
        struct_prompt = f"""
Convert this travel itinerary into structured JSON format with specific landmark names for photo search.

Itinerary:
{result[:3500]}

Return strict JSON ONLY with this schema:
{{
  "destination": "{destination}",
  "days": [
    {{
      "day": 1,
      "title": "Short title (e.g. Shibuya & Shinjuku)",
      "tags": ["Shopping", "Culture"],
      "search_query": "Key landmark name to search photo (e.g. Shibuya Crossing)",
      "description": "2-3 sentences concise description of the day's highlights"
    }}
  ]
}}
"""
        days = []
        try:
            struct_raw = _llm_text("You extract structured travel data. Return strict JSON only.", struct_prompt)
            struct_data = _json_from_llm(struct_raw)
            days = struct_data.get("days", [])
        except Exception as err:
            logger.warning("LLM JSON itinerary extraction failed: %s, using regex parser", err)

        # Regex fallback parser if LLM JSON was empty or failed
        if not days:
            import re
            day_matches = re.findall(r"(?:###\s*)?(?:Day\s*(\d+)[:\s\-]+([^\n\r]+))", result, re.IGNORECASE)
            if day_matches:
                for d_num, d_title in day_matches:
                    clean_title = d_title.strip().replace("*", "").replace("#", "")
                    days.append({
                        "day": int(d_num),
                        "title": clean_title,
                        "tags": ["Highlights", "Culture"],
                        "search_query": clean_title,
                        "description": f"Explore {clean_title} and experience the best local attractions."
                    })
            else:
                days = [
                    {
                        "day": 1,
                        "title": f"Explore {destination}",
                        "tags": ["Highlights", "Culture"],
                        "search_query": destination,
                        "description": f"Discover the iconic sights, culture, and culinary highlights of {destination}."
                    }
                ]

        # Fetch place images for each day
        for d in days:
            q = d.get("search_query", d.get("title", ""))
            d["image_url"] = await fetch_place_image(q, destination)

        return dest_image, days

    dest_image, structured_days = asyncio.run(_enrich_itinerary())

    return {
        "itinerary": result,
        "destination_image": dest_image,
        "structured_itinerary": structured_days,
        "approval_request": approval_request,
        "messages": [AIMessage(content="Draft itinerary created for human review.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
        "agent_trace": [{
            "agent": "itinerary_agent",
            "tools": ["LLM call", "Image Service (Unsplash/Wikipedia)"],
            "summary": f"Draft itinerary with {len(structured_days)} landmark photos generated",
        }],
    }


def human_approval_agent(state: TravelState):
    feedback = interrupt(
        {
            "question": "Do you approve this itinerary?",
            "draft_itinerary": state.get("itinerary", ""),
            "approval_request": state.get("approval_request", ""),
            "expected_response": {
                "approved": True,
                "feedback": "Optional feedback for revision",
            },
        }
    )

    approved = feedback["approved"]
    human_feedback = feedback["feedback"]

    approval_status = "Approved" if approved else "Revisions requested"
    return {
        "approved": approved,
        "human_feedback": human_feedback,
        "messages": [AIMessage(content="Human approval step completed.")],
        "agent_trace": [{
            "agent": "human_approval",
            "tools": ["Human-in-the-loop"],
            "summary": approval_status,
        }],
    }



def final_response_agent(state: TravelState):

    print("\n========== FINAL AGENT INPUT ==========")
    print("Approved:", state.get("approved"))
    print("Feedback:", state.get("human_feedback"))
    print("=======================================\n")

    if state["approved"]:
        prompt = f"""
The human approved this draft itinerary.

Produce the final polished travel plan.

Draft itinerary:
{state['itinerary']}

Budget notes:
{state['budget_results']}
"""
    else:
        prompt = f"""
The human did not approve the draft.

Original user request:
{state['user_query']}

Draft itinerary:
{state['itinerary']}

Human feedback:
{state['human_feedback']}

Budget notes:
{state['budget_results']}
"""

    result = _llm_text(
        "You produce final user-ready travel plans.",
        prompt,
    )

    print("\n========== FINAL RESPONSE ==========")
    print(result)
    print("====================================\n")

    # Reuse or refresh structured itinerary
    structured_days = state.get("structured_itinerary", [])
    dest_image = state.get("destination_image", "")

    return {
        "final_response": result,
        "destination_image": dest_image,
        "structured_itinerary": structured_days,
        "messages": [AIMessage(content=result)],
        "llm_calls": state.get("llm_calls", 0) + 1,
        "agent_trace": [{
            "agent": "final_response",
            "tools": ["LLM call"],
            "summary": "Final polished travel plan generated",
        }],
    }


def output_guardrail_agent(state: TravelState):
    """Validates the final response for quality and safety issues."""
    final_response = state.get("final_response", "")

    if not final_response:
        return {
            "output_guardrail_issues": [],
            "messages": [AIMessage(content="Output guardrail skipped — no response to validate.")],
            "agent_trace": [{
                "agent": "output_guardrail",
                "tools": [],
                "summary": "Skipped — no response",
            }],
        }

    try:
        guardrail_prompt = f"""
Validate this travel plan response for quality and safety.

Response to validate:
{final_response[:4000]}

Check for:
1. Fabricated booking links or fake URLs
2. Made-up prices presented as exact facts (e.g. "Flight costs exactly $342")
3. Unsafe or inappropriate content
4. Off-topic content that is not a travel plan
5. Hallucinated hotel names or airline routes that seem implausible

Return only JSON in this format:
{{
    "safe": true,
    "issues": []
}}

If there are issues, set safe to false and list each issue as a string.
"""

        raw = _llm_text(
            "You are an output safety validator. Return strict JSON only.",
            guardrail_prompt,
        )

        parsed = _json_from_llm(raw)
        is_safe = parsed.get("safe", True)
        issues = parsed.get("issues", [])

        if not is_safe and issues:
            disclaimer = (
                "\n\n---\n"
                "⚠️ **Disclaimer:** This travel plan may contain estimated or "
                "AI-generated information. Please verify all prices, booking "
                "links, and availability with official sources before making "
                "any reservations.\n\n"
                "Flagged issues:\n"
                + "\n".join(f"- {issue}" for issue in issues)
            )
            updated_response = final_response + disclaimer

            return {
                "final_response": updated_response,
                "output_guardrail_issues": issues,
                "messages": [AIMessage(content="Output guardrail flagged issues.")],
                "llm_calls": state.get("llm_calls", 0) + 1,
                "agent_trace": [{
                    "agent": "output_guardrail",
                    "tools": ["Output Validator (LLM)"],
                    "summary": f"Flagged {len(issues)} issue(s)",
                    "error": True,
                }],
            }

        return {
            "output_guardrail_issues": [],
            "messages": [AIMessage(content="Output guardrail passed.")],
            "llm_calls": state.get("llm_calls", 0) + 1,
            "agent_trace": [{
                "agent": "output_guardrail",
                "tools": ["Output Validator (LLM)"],
                "summary": "Response validated — no issues found",
            }],
        }

    except Exception as exc:
        logger.error("Output guardrail failed: %s", exc)
        # If the guardrail itself fails, pass through without blocking
        return {
            "output_guardrail_issues": [],
            "messages": [AIMessage(content="Output guardrail error — passing through.")],
            "agent_trace": [{
                "agent": "output_guardrail",
                "tools": ["Output Validator (LLM)"],
                "summary": f"Guardrail error: {exc}",
                "error": True,
            }],
        }