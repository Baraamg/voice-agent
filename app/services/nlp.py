# app/services/nlp.py
import asyncio
import json
import logging
import re
from typing import Any, Dict, List

from groq import Groq
from app.config import settings
from httpx import HTTPStatusError

logger = logging.getLogger(__name__)


class NLPService:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        # Keep env model first; add a couple of working fallbacks
        self.models: List[str] = [
            settings.LLM_MODEL,
            "llama-3.1-8b-instant",
            "llama-3.1-70b-versatile",
        ]

    async def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze transcribed text using Groq LLM to extract insights.
        Core logic preserved; summary guaranteed.
        """
        defaults: Dict[str, Any] = {
            "topic": "Unknown",
            "sentiment": "neutral",
            "language": "en",
            "action_items": [],
            "summary": "No summary available",
            "confidence_score": 0.8,
        }

        prompt = self._build_prompt(text)

        for model in self.models:
            try:
                # (Kept) first free-form call – you weren't using it, but it's here to keep core the same
                _ = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    messages=[{"role": "user", "content": prompt}],
                    model=model,
                    temperature=0.7,
                    max_tokens=500,
                )

                # Strict JSON call
                chat_completion = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert text analyst. Respond ONLY with a valid JSON object containing insights.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    model=model,
                    temperature=0.2,
                    max_tokens=800,
                    stream=False,
                )

                raw = chat_completion.choices[0].message.content.strip()
                analysis = self._parse_json_safely(raw, defaults)

                # ---- FIX: ensure summary is NOT empty ----
                analysis["summary"] = self._pick_summary(
                    candidate=analysis.get("summary"),
                    original_text=text
                )

                analysis["success"] = True
                return analysis

            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed ({model}): {e}")
            except HTTPStatusError as e:
                logger.error(f"HTTP error ({model}): {e}")
            except Exception as e:
                logger.error(f"NLP analysis failed ({model}): {e}")

        return self._default_analysis(text, "All model attempts failed")

    # ----------------- Helpers -----------------

    def _build_prompt(self, text: str) -> str:
        return f"""You are an expert text analyzer. Analyze the following text and provide insights in a strict JSON format.

Text to analyze: "{text}"

Rules:
- Be concise but informative
- Identify key themes and subjects
- Extract actionable insights
- Keep the summary under 100 words
- If the text appears to be a test message, indicate that in the topic

Required JSON structure:
{{
    "topic": "Main subject or theme of the text",
    "sentiment": "positive/negative/neutral",
    "language": "en/es/etc",
    "action_items": ["Action 1", "Action 2"],
    "summary": "Brief but meaningful summary",
    "confidence_score": 0.95
}}

Respond ONLY with that JSON object.
"""

    def _parse_json_safely(self, raw: str, defaults: Dict[str, Any]) -> Dict[str, Any]:
        # Grab first JSON object if model adds extra text
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            raise json.JSONDecodeError("No JSON object found", raw, 0)

        data = json.loads(match.group(0))
        for k, v in defaults.items():
            if k not in data or data[k] in (None, "", []):
                data[k] = v
        return data

    def _pick_summary(self, candidate: Any, original_text: str) -> str:
        """
        Always return a non-empty summary.
        1) Use candidate if it's a non-empty string.
        2) Else make a quick local summary (first 2 sentences / 60 words max).
        """
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

        # Local fallback: quick heuristic summary (no extra API call)
        text = original_text.strip()
        if not text:
            return "No summary available"

        # Split on sentence-ish punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text)
        summary = " ".join(sentences[:2]).strip()
        if not summary:
            summary = text[:200].strip()

        # hard cap ~60 words
        words = summary.split()
        if len(words) > 60:
            summary = " ".join(words[:60]) + "..."

        return summary or "No summary available"

    def _default_analysis(self, text: str, error: str) -> Dict[str, Any]:
        return {
            "topic": "Analysis failed",
            "sentiment": "neutral",
            "language": "en",
            "action_items": [],
            "summary": "Analysis failed due to an error",
            "confidence_score": 0.0,
            "success": False,
            "error": error,
        }
