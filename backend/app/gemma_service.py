# backend/app/gemma_service.py
import httpx
import json
import logging
from app.config import settings
from app.schemas import GemmaExtractionResponse

# Developer A: Gemma Service for calling the local Ollama Gemma model

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an expert AI assistant for a local kirana (grocery) store in Kerala. 
Your task is to extract order details from customer messages written in Malayalam, Manglish, or English.

Return ONLY valid JSON matching this exact schema:
{
  "schema_version": "1.0",
  "intent": "PLACE_ORDER", // or CORRECTION, CANCEL, GENERAL_CHAT
  "language": "ml-en-mixed", // or ml, en
  "items": [
    {
      "product_mention": "atta",
      "quantity": 2,
      "unit": "kg",
      "variant": null,
      "pack_size_hint": null,
      "source_text": "2 kilo atta",
      "needs_review": false,
      "clarification_question": null
    }
  ],
  "general_notes": []
}

Rules:
- If a product is ambiguous (e.g., "amul butter cheruth" - small amul butter), set needs_review to true and add a clarification_question.
- Do not guess prices or product IDs.
- If the message is not an order, set intent to GENERAL_CHAT and items to [].
- Output strictly JSON. No markdown, no explanations.
"""

async def call_gemma(message_text: str) -> GemmaExtractionResponse:
    """Calls the local Ollama Gemma model and returns validated JSON."""
    url = f"{settings.GEMMA_BASE_URL}/api/chat"
    
    payload = {
        "model": settings.GEMMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message_text}
        ],
        "stream": False,
        "format": "json", # Forces Ollama to output JSON
        "options": {
            "temperature": 0.1
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=settings.GEMMA_TIMEOUT)
            response.raise_for_status()
            
            result = response.json()
            raw_content = result.get("message", {}).get("content", "{}")
            
            # Parse and validate with Pydantic
            parsed_data = json.loads(raw_content)
            return GemmaExtractionResponse(**parsed_data)
            
    except httpx.TimeoutException:
        logger.error("Gemma model timed out")
        raise ValueError("Model inference timed out")
    except json.JSONDecodeError:
        logger.error("Gemma returned invalid JSON")
        raise ValueError("Model returned invalid JSON")
    except Exception as e:
        logger.error(f"Gemma service error: {str(e)}")
        raise ValueError(f"Model service failed: {str(e)}")