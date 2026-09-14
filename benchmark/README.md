# Agentic AI Itinerary Benchmark

This is a standalone evaluation and benchmarking framework for the itinerary-planning AI agent.

## Why this benchmark exists

The purpose of this framework is to evaluate how well the itinerary agent:
1. Selects the correct tools/agents for a given travel request.
2. Extracts correct arguments and constraints.
3. Handles ambiguous requests by asking for clarification.
4. Recovers from tool failures (like MCP connection timeouts).
5. Resists adversarial prompt injection via tool outputs.
6. Produces a useful and complete final itinerary.

## Architecture & Integration

The agent in this repository relies on a **Supervisor pattern**. It does not invoke MCP tools directly via standard LLM tool calling (like OpenAI function calling). Instead:
- The `supervisor_agent` processes the query and outputs `selected_agents` and `trip_constraints`.
- The selected agents (`flight_agent`, `weather_agent`, `hotel_agent`) execute and invoke MCP tools.
- The `flight_agent` unconditionally queries Aviationstack MCP (`list_airports`, `list_airlines`).
- The `hotel_agent` unconditionally queries Tavily for hotels.
- The `weather_agent` unconditionally queries OpenWeather MCP for the destination.

Therefore, this benchmark maps the "tool selection" requirement to the evaluation of `selected_agents`, and the "arguments" requirement to the evaluation of `trip_constraints`.

## Dataset Structure

The benchmark uses JSONL files located in `benchmark/dataset/`. Each line is a test case.
Example:
```json
{
  "id": "weather_001",
  "category": "weather_only",
  "user_input": "What will the weather be like in Rome next week?",
  "expected": {
    "action": "tool_call",
    "acceptable_agents": ["weather_agent"],
    "expected_constraints": {
      "destination": "Rome"
    }
  },
  "evaluation": {
    "task_success": "deterministic"
  }
}
```

## Running the Benchmark

You can run the full benchmark or a specific category.

```bash
# Run all tests
python -m benchmark.runner.benchmark_runner

# Run a specific category
python -m benchmark.runner.benchmark_runner --category weather_only

# Limit number of tests for a quick run
python -m benchmark.runner.benchmark_runner --limit 10

# Compare versions (saves reports under reports/v2)
python -m benchmark.runner.benchmark_runner --agent-version v2
```

## MCP Tool Failures and Simulation

The benchmark intercepts calls to `weather_mcp_search`, `get_airlines`, `tavily_search`, etc. using `unittest.mock.patch` in `mcp_tool_simulator.py`. This ensures:
- The tests run deterministically.
- We can simulate failures like `timeout` or `500_error` safely without relying on production APIs.
- We can inject adversarial prompt injections into the mock responses.

## Sensitive Data

Since this benchmark intercepts API calls before they reach the network and provides mocked responses, it does not use, require, or leak any real API credentials (e.g. `TAVILY_API_KEY`).

## Metrics and Scoring

The benchmark calculates 15 detailed metrics including Tool Selection Accuracy, Argument Accuracy, Latency, and Factual Grounding. A weighted `Overall Score` is generated summarizing performance.
