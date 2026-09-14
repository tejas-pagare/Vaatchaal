import argparse
import asyncio
import json
import logging
import os
import time
from typing import Dict, Any, List
import unittest.mock as mock

import os
os.environ["DATABASE_URL"] = ""

from graph.graph import app
from state.state import TravelState
from langchain_core.messages import HumanMessage

from benchmark.runner.mcp_tool_simulator import simulator
from benchmark.evaluators.evaluators import (
    evaluate_tool_selection,
    evaluate_argument_correctness,
    evaluate_safety,
    evaluate_itinerary_completeness
)
from benchmark.evaluators.judge import evaluate_with_llm
from benchmark.metrics.metrics import BenchmarkMetrics
from benchmark.reports.reporter import generate_reports

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Ensure benchmark directory exists for reports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

def load_dataset(category: str = None, dataset_file: str = None, limit: int = None) -> List[Dict[str, Any]]:
    cases = []
    if dataset_file:
        files = [dataset_file]
    else:
        files = [os.path.join(DATASET_DIR, f) for f in os.listdir(DATASET_DIR) if f.endswith(".jsonl")]
        
    for file in files:
        if not os.path.exists(file):
            logger.warning(f"Dataset file {file} not found.")
            continue
            
        file_cases = []
        with open(file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                case = json.loads(line)
                if category and case.get("category") != category:
                    continue
                file_cases.append(case)
        
        if limit:
            file_cases = file_cases[:limit]
        cases.extend(file_cases)
                
    return cases

def run_single_test(case: Dict[str, Any], metric: str = "all") -> Dict[str, Any]:
    user_input = case["user_input"]
    expected = case["expected"]
    
    # Configure simulator
    simulator.inject_failure(case.get("failure_injection"))
    
    start_time = time.time()
    
    # Initialize state
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "user_query": user_input,
        "flight_results": "",
        "hotel_results": "",
        "weather_results": "",
        "budget_results": "",
        "itinerary": "",
        "llm_calls": 0,
        "agent_trace": [],
        "selected_agents": [],
        "trip_constraints": {}
    }
    
    config = {"configurable": {"thread_id": f"benchmark_{case['id']}"}}
    
    final_state = None
    try:
        final_state = app.invoke(initial_state, config=config)
    except Exception as e:
        logger.error(f"Graph execution failed for {case['id']}: {e}")
        final_state = initial_state # Fallback
        
    latency_ms = (time.time() - start_time) * 1000
    
    # Extract outcomes
    trace = final_state.get("agent_trace", [])
    constraints = final_state.get("trip_constraints", {})
    final_response = final_state.get("final_response", "")
    llm_calls = final_state.get("llm_calls", 0)
    
    # Number of MCP tools actually called is represented by trace entries for specialist agents
    tool_call_count = len([t for t in trace if t.get("agent") not in ("supervisor", "human_approval", "final_response", "output_guardrail")])
    
    # Run Evaluators
    eval_results = {}
    
    # 1. Tool selection
    if metric in ["all", "tool_selection"]:
        ts_eval = evaluate_tool_selection(expected, trace)
        eval_results["tool_selection"] = ts_eval
    
    # 2. Argument correctness
    if metric in ["all", "argument_correctness"]:
        arg_eval = evaluate_argument_correctness(expected, constraints)
        eval_results["argument_correctness"] = arg_eval
    
    # 3. Completeness
    if metric in ["all", "itinerary_completeness"]:
        comp_eval = evaluate_itinerary_completeness(final_response, expected)
        eval_results["itinerary_completeness"] = comp_eval
    
    # 4. Safety
    if metric in ["all", "safety"]:
        safety_eval = evaluate_safety(final_response, trace)
        eval_results["safety"] = safety_eval
    
    # 5. Task Success (Deterministic or LLM Judge)
    if metric in ["all", "task_success"]:
        eval_type = case.get("evaluation", {}).get("task_success", "deterministic")
        
        if eval_type == "deterministic":
            ts_correct = eval_results.get("tool_selection", {}).get("correct", True)
            arg_correct = eval_results.get("argument_correctness", {}).get("correct", True)
            comp_correct = eval_results.get("itinerary_completeness", {}).get("correct", True)
            is_success = ts_correct and arg_correct and comp_correct
            eval_results["task_success"] = {
                "correct": is_success,
                "is_grounded": True,
                "reason": "Deterministic evaluation passed" if is_success else "Deterministic checks failed"
            }
        else:
            judge_res = evaluate_with_llm(user_input, expected, final_response, trace)
            eval_results["task_success"] = judge_res
        
    result = {
        "id": case["id"],
        "category": case["category"],
        "user_input": user_input,
        "latency_ms": latency_ms,
        "llm_calls": llm_calls,
        "tool_call_count": tool_call_count,
        "trace": trace,
        "final_response": final_response,
        **eval_results
    }
    
    return result

def main():
    parser = argparse.ArgumentParser(description="Agentic AI Itinerary Benchmark")
    parser.add_argument("--category", type=str, help="Run specific category (e.g., weather_only)")
    parser.add_argument("--dataset", type=str, help="Run specific dataset file")
    parser.add_argument("--limit", type=int, help="Limit number of tests")
    parser.add_argument("--agent-version", type=str, default="v1", help="Agent version for reporting")
    parser.add_argument("--metric", type=str, default="all", help="Evaluate a specific metric")
    args = parser.parse_args()

    cases = load_dataset(category=args.category, dataset_file=args.dataset, limit=args.limit)
    if not cases:
        logger.error("No test cases found.")
        return

    logger.info(f"Loaded {len(cases)} test cases.")

    metrics = BenchmarkMetrics()
    
    # Apply patches
    patchers = [
        mock.patch("agents.agent.weather_mcp_search", new=simulator.mock_weather_mcp_search),
        mock.patch("agents.agent.forecast_mcp_search", new=simulator.mock_forecast_mcp_search),
        mock.patch("agents.agent.get_airlines", new=simulator.mock_get_airlines),
        mock.patch("agents.agent.get_airports", new=simulator.mock_get_airports),
        mock.patch("agents.agent.tavily_search", new=simulator.mock_tavily_search),
        # Bypass human in the loop for benchmark
        mock.patch("agents.agent.interrupt", return_value={"approved": True, "feedback": ""})
    ]
    
    for p in patchers:
        p.start()

    try:
        for i, case in enumerate(cases):
            logger.info(f"Running test {i+1}/{len(cases)}: {case['id']}")
            result = run_single_test(case, metric=args.metric)
            metrics.add_result(result)
            time.sleep(2)  # Avoid rate limits
            
    finally:
        for p in patchers:
            p.stop()

    computed_metrics = metrics.compute()
    
    report_dir = os.path.join(REPORTS_DIR, args.agent_version)
    generate_reports(metrics.results, computed_metrics, report_dir)

if __name__ == "__main__":
    main()
