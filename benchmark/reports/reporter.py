import json
import csv
import os
from typing import Dict, Any, List

def format_percentage(val: float) -> str:
    return f"{val * 100:.1f}%"

def generate_reports(results: List[Dict[str, Any]], metrics: Dict[str, Any], output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    
    # JSON Report
    json_path = os.path.join(output_dir, "latest.json")
    with open(json_path, "w") as f:
        json.dump({"metrics": metrics, "results": results}, f, indent=2)

    # CSV Report
    csv_path = os.path.join(output_dir, "latest.csv")
    with open(csv_path, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(metrics.keys())
        writer.writerow(metrics.values())

    # Terminal Report
    failed_cases = [r for r in results if not r.get("task_success", {}).get("correct", False)]
    
    print("\n" + "="*50)
    print(f"{'ITINERARY AGENT BENCHMARK RESULTS':^50}")
    print("="*50)
    print()
    print(f"{'Total Tests':<30} {metrics['total_tests']}")
    print(f"{'Passed':<30} {metrics['passed']}")
    print(f"{'Failed':<30} {metrics['failed']}")
    print()
    print(f"{'Itinerary Task Success':<30} {format_percentage(metrics['itinerary_task_success'])}")
    print(f"{'Tool Selection Accuracy':<30} {format_percentage(metrics['tool_selection_accuracy'])}")
    print(f"{'Argument Accuracy':<30} {format_percentage(metrics['argument_accuracy'])}")
    print(f"{'Itinerary Completeness':<30} {format_percentage(metrics['itinerary_completeness'])}")
    print(f"{'No-Tool Precision':<30} {format_percentage(metrics['no_tool_precision'])}")
    print(f"{'Clarification Accuracy':<30} {format_percentage(metrics['clarification_accuracy'])}")
    print(f"{'Recovery Rate':<30} {format_percentage(metrics['recovery_rate'])}")
    print()
    print(f"{'Weather Tool Accuracy':<30} {format_percentage(metrics['weather_tool_accuracy'])}")
    print(f"{'Flight Tool Accuracy':<30} {format_percentage(metrics['flight_tool_accuracy'])}")
    print(f"{'Tavily Tool Accuracy':<30} {format_percentage(metrics['tavily_tool_accuracy'])}")
    print()
    print(f"{'Average Tool Calls':<30} {metrics['avg_tool_calls']:.2f}")
    print(f"{'Median Tool Calls':<30} {metrics['median_tool_calls']}")
    print(f"{'P95 Tool Calls':<30} {metrics['p95_tool_calls']}")
    print()
    print(f"{'Average Latency':<30} {metrics['avg_latency_sec']:.2f} sec")
    print(f"{'P95 Latency':<30} {metrics['p95_latency_sec']:.2f} sec")
    print()
    print(f"{'Average Tokens (Proxy)':<30} {metrics['avg_tokens']}")
    print()
    print(f"{'Injection Resistance':<30} {format_percentage(metrics['injection_resistance'])}")
    print(f"{'Factual Grounding':<30} {format_percentage(metrics['factual_grounding'])}")
    print(f"{'Overall Score':<30} {format_percentage(metrics['overall_score'])}")
    print("\n" + "="*50)
    
    if failed_cases:
        print("\nFAILED CASES")
        print("-" * 50)
        for i, fc in enumerate(failed_cases[:10]): # Show up to 10 failed cases
            print(f"\n{fc['id']}")
            print(f"Category: {fc['category']}")
            print(f"User request:\n{fc['user_input']}")
            ts_reason = fc.get("tool_selection", {}).get("reason", "")
            if ts_reason:
                print(f"Tool Selection Error: {ts_reason}")
            ts_succ = fc.get("task_success", {}).get("reason", "")
            if ts_succ:
                print(f"Task Success Error: {ts_succ}")
            print("-" * 50)
        if len(failed_cases) > 10:
            print(f"... and {len(failed_cases) - 10} more.")
