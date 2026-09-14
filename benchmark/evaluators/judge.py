import json
import logging
from typing import Dict, Any

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

def get_judge_llm():
    try:
        from config.llm import get_llm
        return get_llm()
    except Exception as e:
        logger.warning(f"Could not load get_llm from config: {e}. Attempting fallback.")
        import os
        return ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model="openai/gpt-oss-20b"
        )

def evaluate_with_llm(user_input: str, expected: Dict[str, Any], final_response: str, trace: list) -> Dict[str, Any]:
    llm = get_judge_llm()
    
    prompt = f"""
You are an expert evaluator for an AI travel agent benchmark.
Evaluate the following final response from the agent based on the user's request and expected behavior.

User Request: {user_input}
Expected Behavior Category: {expected.get('action')}
Expected details: {json.dumps(expected)}

Agent Final Response:
{final_response}

Agent Internal Trace (Agents used):
{json.dumps([t.get('agent') for t in trace])}

Evaluate the response based on the following criteria:
1. Did the agent successfully accomplish the task? (task_success)
2. Is the response grounded in facts and not hallucinated? (is_grounded)
3. For failure recovery or ambiguous requests, did the agent handle it gracefully?

Return ONLY strict JSON with this exact schema:
{{
  "correct": true/false,
  "score": float between 0.0 and 1.0,
  "covers_flights": true/false,
  "covers_weather": true/false,
  "covers_recommendations": true/false,
  "is_grounded": true/false,
  "reason": "Short explanation of the evaluation"
}}
"""
    try:
        response = llm.invoke([
            SystemMessage(content="You are a strict JSON-only evaluator. Output nothing but JSON."),
            HumanMessage(content=prompt)
        ])
        
        # Parse JSON from response
        content = response.content
        if "{" in content:
            start = content.index("{")
            end = content.rindex("}") + 1
            content = content[start:end]
            
        return json.loads(content)
    except Exception as e:
        logger.error(f"LLM Judge evaluation failed: {e}")
        return {
            "correct": False,
            "score": 0.0,
            "reason": f"Judge error: {str(e)}",
            "is_grounded": False
        }
