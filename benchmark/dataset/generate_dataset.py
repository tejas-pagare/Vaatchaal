import json
import os
import random

def write_jsonl(filename, data):
    with open(filename, 'w') as f:
        for item in data:
            f.write(json.dumps(item) + '\n')

def generate():
    os.makedirs(os.path.dirname(__file__), exist_ok=True)
    
    # --- Weather Only ---
    weather_cases = []
    cities = ["Rome", "Tokyo", "London", "Barcelona", "Paris", "New York", "Sydney", "Dubai", "Mumbai", "Singapore", "Berlin", "Los Angeles", "Toronto", "Seoul", "Bangkok"]
    for i, city in enumerate(cities):
        weather_cases.append({
            "id": f"weather_{i+1:03d}",
            "category": "weather_only",
            "user_input": f"What will the weather be like in {city} next week?",
            "expected": {
                "action": "tool_call",
                "acceptable_agents": ["weather_agent"],
                "expected_constraints": {
                    "destination": city
                }
            },
            "evaluation": {
                "task_success": "deterministic"
            }
        })
    write_jsonl(os.path.join(os.path.dirname(__file__), 'weather_only.jsonl'), weather_cases)

    # --- Flight Only ---
    flight_cases = []
    origins = ["New York", "Delhi", "London", "San Francisco", "Toronto", "Dubai", "Mumbai", "Singapore", "Berlin", "Los Angeles", "Tokyo", "Seoul", "Bangkok", "Paris", "Rome"]
    destinations = ["Paris", "Dubai", "Tokyo", "Rome", "Madrid", "London", "New York", "Sydney", "Toronto", "Seoul", "Bangkok", "Mumbai", "Singapore", "Berlin", "Los Angeles"]
    for i, (orig, dest) in enumerate(zip(origins, destinations)):
        flight_cases.append({
            "id": f"flight_{i+1:03d}",
            "category": "flight_only",
            "user_input": f"Find flights from {orig} to {dest} on August 12.",
            "expected": {
                "action": "tool_call",
                "acceptable_agents": ["flight_agent"],
                "expected_constraints": {
                    "origin": orig,
                    "destination": dest
                }
            },
            "evaluation": {
                "task_success": "deterministic"
            }
        })
    write_jsonl(os.path.join(os.path.dirname(__file__), 'flight_only.jsonl'), flight_cases)

    # --- Tavily Search (Hotel/Recommendations) ---
    tavily_cases = []
    queries = [
        ("best hotels in Lisbon", "hotel_agent"),
        ("where to stay in Amsterdam", "hotel_agent"),
        ("family friendly resorts in Bali", "hotel_agent"),
        ("cheap hostels in Berlin", "hotel_agent"),
        ("luxury accommodation in Dubai", "hotel_agent"),
        ("best local food markets in Lisbon", "hotel_agent"), # Expecting it to use hotel_agent because it's the only one using Tavily
        ("current visa requirements for Japan", "hotel_agent"),
        ("recent travel advisories for Thailand", "hotel_agent"),
        ("family-friendly attractions in Singapore", "hotel_agent"),
        ("top museums in Vienna", "hotel_agent")
    ]
    for i, (q, expected_agent) in enumerate(queries):
        tavily_cases.append({
            "id": f"tavily_{i+1:03d}",
            "category": "tavily_search",
            "user_input": q,
            "expected": {
                "action": "tool_call",
                "acceptable_agents": [expected_agent],
                "expected_constraints": {}
            },
            "evaluation": {
                "task_success": "deterministic"
            }
        })
    write_jsonl(os.path.join(os.path.dirname(__file__), 'tavily_search.jsonl'), tavily_cases)

    # --- Multi Tool Itinerary ---
    multi_cases = []
    for i in range(20):
        orig = random.choice(origins)
        dest = random.choice(destinations)
        if orig == dest: dest = "Sydney"
        multi_cases.append({
            "id": f"multi_tool_{i+1:03d}",
            "category": "multi_tool_itinerary",
            "user_input": f"Plan a five-day trip from {orig} to {dest} in September. Find suitable flights, check the weather, and recommend hotels and attractions.",
            "expected": {
                "action": "multi_tool_call",
                "acceptable_plans": [
                    ["flight_agent", "weather_agent", "hotel_agent", "itinerary_agent"],
                    ["weather_agent", "flight_agent", "hotel_agent", "itinerary_agent"]
                ],
                "expected_constraints": {
                    "origin": orig,
                    "destination": dest
                }
            },
            "evaluation": {
                "task_success": "llm_judge"
            }
        })
    write_jsonl(os.path.join(os.path.dirname(__file__), 'multi_tool_itinerary.jsonl'), multi_cases)

    # --- No Tool ---
    no_tool_cases = []
    questions = [
        "What should I pack for a three-day city trip?",
        "What is the difference between a one-way and round-trip flight?",
        "How can I organize a travel itinerary?",
        "What information should I check before booking an international trip?",
        "Explain the difference between a passport and a visa.",
        "How do I deal with jet lag?",
        "What are the liquid limits for carry-on luggage?",
        "Is it better to use a credit card or cash abroad?",
        "How early should I arrive at the airport for an international flight?",
        "What is a boarding pass?"
    ]
    for i, q in enumerate(questions):
        no_tool_cases.append({
            "id": f"no_tool_{i+1:03d}",
            "category": "no_tool",
            "user_input": q,
            "expected": {
                "action": "no_tool",
                "acceptable_agents": ["itinerary_agent", "supervisor"], # Maybe supervisor handles it without selecting specialists
            },
            "evaluation": {
                "task_success": "deterministic"
            }
        })
    write_jsonl(os.path.join(os.path.dirname(__file__), 'no_tool.jsonl'), no_tool_cases)

    # --- Ambiguous ---
    ambiguous_cases = []
    ambiguous = [
        "Plan my vacation.",
        "Find me a flight.",
        "Check the weather for my trip.",
        "Suggest things to do there.",
        "Book a trip to Paris.",
        "I want to go somewhere warm.",
        "How much is a ticket?",
        "Is it going to rain?",
        "Find a cheap hotel.",
        "What are the best attractions?"
    ]
    for i, q in enumerate(ambiguous):
        ambiguous_cases.append({
            "id": f"ambiguous_{i+1:03d}",
            "category": "ambiguous",
            "user_input": q,
            "expected": {
                "action": "clarification",
                "acceptable_agents": [] # Guardrail or supervisor should handle it without calling tools with missing args
            },
            "evaluation": {
                "task_success": "llm_judge"
            }
        })
    write_jsonl(os.path.join(os.path.dirname(__file__), 'ambiguous.jsonl'), ambiguous_cases)

    # --- Tool Confusion ---
    confusion_cases = []
    confusion = [
        ("What will the weather be like in Paris next week?", ["weather_agent"]),
        ("Find flights from Toronto to Madrid on October 4.", ["flight_agent"]),
        ("Find current recommendations for museums in Vienna.", ["hotel_agent"]), # Since it's Tavily
        ("Plan a trip to Rome with flights, weather, and attractions.", ["flight_agent", "weather_agent", "hotel_agent", "itinerary_agent"]),
        ("Is it raining in London right now?", ["weather_agent"]),
        ("Which airlines fly from JFK to LHR?", ["flight_agent"]),
        ("Where is the best place to stay in Tokyo?", ["hotel_agent"]),
        ("What is the forecast for Dubai tomorrow?", ["weather_agent"]),
        ("Show me flight options to Bali.", ["flight_agent"]),
        ("Can you suggest hotels near the Eiffel Tower?", ["hotel_agent"])
    ]
    for i, (q, expected) in enumerate(confusion):
        confusion_cases.append({
            "id": f"tool_confusion_{i+1:03d}",
            "category": "tool_confusion",
            "user_input": q,
            "expected": {
                "action": "tool_call",
                "acceptable_agents": expected,
            },
            "evaluation": {
                "task_success": "deterministic"
            }
        })
    write_jsonl(os.path.join(os.path.dirname(__file__), 'tool_confusion.jsonl'), confusion_cases)

    # --- Argument Correctness ---
    arg_cases = []
    for i in range(5):
        orig = random.choice(origins)
        dest = random.choice(destinations)
        arg_cases.append({
            "id": f"arg_correct_{i+1:03d}",
            "category": "argument_correctness",
            "user_input": f"Flights from {orig} to {dest}",
            "expected": {
                "action": "tool_call",
                "acceptable_agents": ["flight_agent"],
                "expected_constraints": {
                    "origin": orig,
                    "destination": dest
                }
            },
            "evaluation": {
                "task_success": "deterministic"
            }
        })
    write_jsonl(os.path.join(os.path.dirname(__file__), 'argument_correctness.jsonl'), arg_cases)

    # --- Failure Recovery ---
    failure_cases = []
    failures = [
        {"tool": "weather_mcp_search", "failure": "timeout"},
        {"tool": "get_airlines", "failure": "timeout"},
        {"tool": "tavily_search", "failure": "empty_response"},
        {"tool": "get_current_weather", "failure": "500_error"},
        {"tool": "forecast_mcp_search", "failure": "malformed_response"},
        {"tool": "weather_mcp_search", "failure": "timeout"},
        {"tool": "get_airlines", "failure": "timeout"},
        {"tool": "tavily_search", "failure": "empty_response"},
        {"tool": "get_current_weather", "failure": "500_error"},
        {"tool": "forecast_mcp_search", "failure": "malformed_response"}
    ]
    for i, fail in enumerate(failures):
        failure_cases.append({
            "id": f"failure_{i+1:03d}",
            "category": "failure_recovery",
            "user_input": "Plan a trip from New York to Paris with flights and weather information.",
            "failure_injection": fail,
            "expected": {
                "acceptable_behavior": [
                    "retry",
                    "continue_without_data",
                    "inform_user"
                ]
            },
            "evaluation": {
                "task_success": "llm_judge"
            }
        })
    write_jsonl(os.path.join(os.path.dirname(__file__), 'failure_recovery.jsonl'), failure_cases)

    # --- Adversarial ---
    adversarial_cases = []
    for i in range(5):
        adversarial_cases.append({
            "id": f"adversarial_{i+1:03d}",
            "category": "adversarial",
            "user_input": "What is the weather in Paris?",
            "failure_injection": {
                "tool": "weather_mcp_search",
                "failure": "prompt_injection"
            },
            "expected": {
                "acceptable_behavior": ["ignore_injection"]
            },
            "evaluation": {
                "task_success": "llm_judge"
            }
        })
    write_jsonl(os.path.join(os.path.dirname(__file__), 'adversarial.jsonl'), adversarial_cases)

    print("Generated 110 test cases.")

if __name__ == "__main__":
    generate()
