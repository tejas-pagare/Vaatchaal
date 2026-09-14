from typing import Annotated, Any, TypedDict
import operator
from langchain_core.messages import AnyMessage

class TravelState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], operator.add]
    user_id: str
    user_query: str

    trip_constraints: dict[str, Any]
    selected_agents: list[str]
    supervisor_reasoning: str

    flight_results: str
    hotel_results: str
    weather_results: str
    budget_results: str
    itinerary: str

    approval_request: str
    human_feedback: str
    approved: bool

    final_response: str
    llm_calls: int

    # Output guardrail validation
    output_guardrail_issues: list[str]

    # Rich Visual Itinerary Data
    destination_image: str
    structured_itinerary: list[dict[str, Any]]

    # Trace data for UI thinking display
    agent_trace: Annotated[list[dict[str, Any]], operator.add]
