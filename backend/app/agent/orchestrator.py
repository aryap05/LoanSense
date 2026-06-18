import os
import json
import logging
import httpx
from sqlalchemy.orm import Session
from app.db import crud
from app.agent.tools import execute_tool_call
from app.agent.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

OPENAI_LOAN_ASSESSMENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_credit_risk_score",
            "description": "Returns the credit risk score and risk band for the loan applicant. Score ranges from 0 (no risk) to 1 (high risk). Risk bands: Low (<0.3), Medium (0.3-0.6), High (>0.6).",
            "parameters": {
                "type": "object",
                "properties": {
                    "applicant_id": {"type": "string"}
                },
                "required": ["applicant_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_fraud_signals",
            "description": "Returns fraud probability and specific fraud signal flags triggered for the applicant. Signals include: income_fabrication_risk, high_enquiry_velocity, new_account_high_score, transaction_velocity_anomaly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "applicant_id": {"type": "string"}
                },
                "required": ["applicant_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_contradiction_score",
            "description": "Returns the contradiction score quantifying the tension between credit and fraud signals. Also returns the contradiction type and specific rule flags fired. A score above 0.6 indicates a significant contradiction requiring human review.",
            "parameters": {
                "type": "object",
                "properties": {
                    "applicant_id": {"type": "string"}
                },
                "required": ["applicant_id"]
            }
        }
    }
]

class AgentOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model_name = "llama-3.3-70b-versatile"
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    async def assess(self, applicant_id: str, applicant_context: str) -> dict:
        """
        Runs the full assessment loop with Groq.
        Returns the structured verdict dictionary.
        """
        if not self.api_key:
            logger.error("GROQ_API_KEY environment variable not set.")
            raise ValueError("GROQ_API_KEY is not set in the environment variables.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": applicant_context}
        ]
        
        contradiction_score = 0.0

        try:
            async with httpx.AsyncClient() as client:
                while True:
                    payload = {
                        "model": self.model_name,
                        "messages": messages,
                        "temperature": 0.0,
                        "tools": OPENAI_LOAN_ASSESSMENT_TOOLS,
                        "tool_choice": "auto"
                    }
                    
                    response = await client.post(self.api_url, headers=headers, json=payload, timeout=60.0)
                    if response.status_code != 200:
                        raise Exception(f"Groq API error {response.status_code}: {response.text}")
                        
                    response_data = response.json()
                    message = response_data["choices"][0]["message"]
                    
                    # Add assistant message to history
                    messages.append(message)
                    
                    if "tool_calls" in message and message["tool_calls"]:
                        for tool_call in message["tool_calls"]:
                            tool_name = tool_call["function"]["name"]
                            args_str = tool_call["function"]["arguments"]
                            try:
                                args = json.loads(args_str)
                            except json.JSONDecodeError:
                                args = {}
                                
                            app_id_arg = args.get("applicant_id", applicant_id)
                            
                            # Execute tool
                            result = execute_tool_call(tool_name, app_id_arg, self.db)
                            
                            # Capture contradiction score if available
                            if tool_name == "get_contradiction_score" and "contradiction_score" in result:
                                try:
                                    contradiction_score = float(result["contradiction_score"])
                                except (ValueError, TypeError):
                                    pass
                                    
                            # Add tool response to history
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "name": tool_name,
                                "content": json.dumps(result)
                            })
                    else:
                        # No more tool calls, we have the final answer
                        raw_text = message.get("content", "").strip()
                        break
                        
            # 3. Parse final JSON response
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()
            
            verdict_json = json.loads(raw_text)
            
            # 4. ENFORCE: Contradiction Hard Rule
            if contradiction_score > 0.6 and verdict_json.get("decision") == "APPROVE":
                verdict_json["decision"] = "FLAG_FOR_REVIEW"
                verdict_json["primary_reason"] = f"OVERRIDE: Agent approved, but contradiction score ({contradiction_score:.2f}) exceeded the 0.6 safety threshold."
                # Log override event
                crud.create_audit_log(
                    db=self.db,
                    applicant_id=applicant_id,
                    event_type="verdict_override",
                    event_data={
                        "original_decision": "APPROVE",
                        "new_decision": "FLAG_FOR_REVIEW",
                        "contradiction_score": contradiction_score
                    }
                )
                
            return verdict_json
            
        except Exception as e:
            logger.error(f"Agent Orchestrator failed for applicant {applicant_id}: {str(e)}")
            # On API error or JSON parse failure: return a safe fallback verdict
            return {
                "decision": "FLAG_FOR_REVIEW",
                "confidence": 0.0,
                "primary_reason": "SYSTEM FALLBACK: Agent assessment failed or returned invalid response format.",
                "risk_signals": {
                    "fraud": False,
                    "other_flags": [f"Error: {str(e)}"]
                },
                "rbi_mapping": {
                    "section": "Internal Credit Policy (Manual Override)"
                },
                "what_would_change": "Manual review required due to system failure."
            }

