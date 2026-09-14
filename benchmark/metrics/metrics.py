from typing import List, Dict, Any

class BenchmarkMetrics:
    def __init__(self):
        self.results = []

    def add_result(self, result: Dict[str, Any]):
        self.results.append(result)

    def compute(self) -> Dict[str, Any]:
        total = len(self.results)
        if total == 0:
            return {}

        passed = sum(1 for r in self.results if r.get("task_success", {}).get("correct", False))
        
        # Tool Selection Accuracy
        tool_selection_cases = [r for r in self.results if r["category"] not in ["failure_recovery", "adversarial"]]
        correct_tool_selections = sum(1 for r in tool_selection_cases if r.get("tool_selection", {}).get("correct", False))
        tool_selection_accuracy = correct_tool_selections / max(1, len(tool_selection_cases))

        # Argument Accuracy
        arg_cases = [r for r in self.results if "argument_correctness" in r]
        correct_args = sum(1 for r in arg_cases if r.get("argument_correctness", {}).get("correct", False))
        argument_accuracy = correct_args / max(1, len(arg_cases))

        # Itinerary Completeness
        completeness_cases = [r for r in self.results if "itinerary_completeness" in r]
        correct_completeness = sum(1 for r in completeness_cases if r.get("itinerary_completeness", {}).get("correct", False))
        completeness_accuracy = correct_completeness / max(1, len(completeness_cases))

        # No-Tool Precision
        no_tool_cases = [r for r in self.results if r["category"] == "no_tool"]
        correct_no_tool = sum(1 for r in no_tool_cases if r.get("tool_selection", {}).get("correct", False))
        no_tool_precision = correct_no_tool / max(1, len(no_tool_cases))

        # Clarification Accuracy
        ambiguous_cases = [r for r in self.results if r["category"] == "ambiguous"]
        correct_clarification = sum(1 for r in ambiguous_cases if r.get("tool_selection", {}).get("correct", False))
        clarification_accuracy = correct_clarification / max(1, len(ambiguous_cases))

        # Recovery Rate
        recovery_cases = [r for r in self.results if r["category"] == "failure_recovery"]
        successful_recoveries = sum(1 for r in recovery_cases if r.get("task_success", {}).get("correct", False))
        recovery_rate = successful_recoveries / max(1, len(recovery_cases))

        # Safety / Injection Resistance
        adversarial_cases = [r for r in self.results if r["category"] == "adversarial"]
        safe_cases = sum(1 for r in adversarial_cases if r.get("safety", {}).get("is_safe", True))
        injection_resistance = safe_cases / max(1, len(adversarial_cases))

        # Latency
        latencies = [r.get("latency_ms", 0) for r in self.results]
        avg_latency = sum(latencies) / max(1, len(latencies))
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

        # Token Usage
        tokens = [r.get("llm_calls", 0) * 500 for r in self.results] # Proxy for tokens if not explicitly available
        avg_tokens = sum(tokens) / max(1, len(tokens))

        # Tool calls
        tool_counts = [r.get("tool_call_count", 0) for r in self.results]
        avg_tool_calls = sum(tool_counts) / max(1, len(tool_counts))
        median_tool_calls = sorted(tool_counts)[len(tool_counts) // 2] if tool_counts else 0
        p95_tool_calls = sorted(tool_counts)[int(len(tool_counts) * 0.95)] if tool_counts else 0

        # Per tool accuracy
        weather_cases = [r for r in tool_selection_cases if r["category"] == "weather_only"]
        weather_acc = sum(1 for r in weather_cases if r.get("tool_selection", {}).get("correct", False)) / max(1, len(weather_cases))

        flight_cases = [r for r in tool_selection_cases if r["category"] == "flight_only"]
        flight_acc = sum(1 for r in flight_cases if r.get("tool_selection", {}).get("correct", False)) / max(1, len(flight_cases))

        tavily_cases = [r for r in tool_selection_cases if r["category"] == "tavily_search"]
        tavily_acc = sum(1 for r in tavily_cases if r.get("tool_selection", {}).get("correct", False)) / max(1, len(tavily_cases))

        itinerary_task_success = passed / total
        factual_grounding = sum(1 for r in self.results if r.get("task_success", {}).get("is_grounded", True)) / max(1, len(self.results))

        score = (
            itinerary_task_success * 0.30 +
            tool_selection_accuracy * 0.25 +
            argument_accuracy * 0.15 +
            completeness_accuracy * 0.10 +
            (1.0 if avg_tool_calls <= 3 else 0.5) * 0.05 + # Rough proxy for tool efficiency
            recovery_rate * 0.05 +
            clarification_accuracy * 0.05 +
            no_tool_precision * 0.05
        )

        return {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "itinerary_task_success": itinerary_task_success,
            "tool_selection_accuracy": tool_selection_accuracy,
            "argument_accuracy": argument_accuracy,
            "itinerary_completeness": completeness_accuracy,
            "no_tool_precision": no_tool_precision,
            "clarification_accuracy": clarification_accuracy,
            "recovery_rate": recovery_rate,
            "weather_tool_accuracy": weather_acc,
            "flight_tool_accuracy": flight_acc,
            "tavily_tool_accuracy": tavily_acc,
            "avg_tool_calls": avg_tool_calls,
            "median_tool_calls": median_tool_calls,
            "p95_tool_calls": p95_tool_calls,
            "avg_latency_sec": avg_latency / 1000.0,
            "p95_latency_sec": p95_latency / 1000.0,
            "avg_tokens": avg_tokens,
            "injection_resistance": injection_resistance,
            "factual_grounding": factual_grounding,
            "overall_score": score
        }
