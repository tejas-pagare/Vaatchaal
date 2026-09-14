import unittest
from benchmark.evaluators.evaluators import evaluate_tool_selection, evaluate_argument_correctness

class TestEvaluators(unittest.TestCase):
    
    def test_tool_selection_correct(self):
        expected = {
            "action": "tool_call",
            "acceptable_agents": ["weather_agent"]
        }
        trace = [{"agent": "weather_agent"}]
        res = evaluate_tool_selection(expected, trace)
        self.assertTrue(res["correct"])
        
    def test_tool_selection_incorrect(self):
        expected = {
            "action": "tool_call",
            "acceptable_agents": ["weather_agent"]
        }
        trace = [{"agent": "tavily_search"}]
        res = evaluate_tool_selection(expected, trace)
        self.assertFalse(res["correct"])
        
    def test_argument_correctness(self):
        expected = {
            "expected_constraints": {
                "destination": "Paris"
            }
        }
        constraints = {"destination": "Paris, France"}
        res = evaluate_argument_correctness(expected, constraints)
        self.assertTrue(res["correct"])
        
    def test_argument_incorrect(self):
        expected = {
            "expected_constraints": {
                "origin": "London"
            }
        }
        constraints = {"origin": "Paris"}
        res = evaluate_argument_correctness(expected, constraints)
        self.assertFalse(res["correct"])
        
if __name__ == '__main__':
    unittest.main()
