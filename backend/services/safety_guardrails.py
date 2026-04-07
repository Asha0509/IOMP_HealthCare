"""
Safety Guardrails Engine
------------------------
Uses Gemini API for intelligent crisis and emergency detection.
Only intervenes for true emergencies (self-harm, life-threatening conditions).
"""

import json
import re
from typing import List, Dict, Optional, Tuple
from core.config import settings
from core.logging import app_logger
from services.llm_client import generate_json_with_fallback, has_any_provider

CRISIS_HOTLINES = {
    "en": {
        "message": "I'm very concerned about what you've shared. You are not alone and help is available right now.",
        "resources": [
            {"name": "iCall (India)", "number": "9152987821", "available": "Mon-Sat 8am-10pm"},
            {"name": "Vandrevala Foundation", "number": "1860-2662-345", "available": "24/7"},
            {"name": "AASRA", "number": "9820466627", "available": "24/7"},
        ],
    },
    "hi": {
        "message": "आपकी बात सुनकर मैं बहुत चिंतित हूं। आप अकेले नहीं हैं, मदद उपलब्ध है।",
        "resources": [
            {"name": "iCall", "number": "9152987821", "available": "सोम-शनि सुबह 8 बजे से रात 10 बजे"},
            {"name": "Vandrevala Foundation", "number": "1860-2662-345", "available": "24/7"},
        ],
    },
}


def _check_hardcoded_medical_emergency(text: str) -> Optional[str]:
    """
    Deterministic medical emergency trigger for severe cardiac-sounding complaints.
    Returns a human-readable reason if matched.
    """
    if not text:
        return None

    normalized = " ".join(text.lower().strip().split())

    has_intensity = bool(re.search(r"\b(intense|severe|extreme|crushing|unbearable|worst)\b", normalized))
    has_heart_ache = bool(re.search(r"\bheart[\s-]?ache\b", normalized))
    has_chest_pain = bool(re.search(r"\bchest\s+pain\b", normalized))

    if has_intensity and (has_heart_ache or has_chest_pain):
        return "Potential cardiac emergency detected from severe chest/heart pain wording"

    if "intense heart ache" in normalized or "intense heartache" in normalized:
        return "Potential cardiac emergency detected from intense heart ache wording"

    return None


def check_crisis_gemini(text: str, intent: str, symptoms: List[str]) -> Optional[Dict]:
    """Use Gemini to intelligently detect crisis situations."""
    if not has_any_provider():
        # Fallback to keyword detection
        crisis_keywords = ["suicide", "kill myself", "want to die", "end my life", "self harm"]
        text_lower = text.lower()
        if any(kw in text_lower for kw in crisis_keywords) or intent == "crisis":
            return {"is_crisis": True, "reason": "Crisis indicators detected"}
        return None
    
    prompt = f"""Analyze this text for mental health crisis indicators.

Text: "{text}"
Detected intent: {intent}
Symptoms mentioned: {', '.join(symptoms) if symptoms else 'none'}

Is this person expressing:
1. Suicidal thoughts or intentions
2. Self-harm ideation
3. Immediate danger to themselves

Respond ONLY with JSON:
{{"is_crisis": true/false, "reason": "brief explanation if crisis detected"}}

Be careful not to over-flag. Only return is_crisis=true for genuine self-harm or suicidal expressions.
Medical symptoms (even severe ones) should NOT be flagged as crisis - that's handled separately."""

    try:
        result, _provider = generate_json_with_fallback(
            prompt=prompt,
            default={"is_crisis": False},
            temperature=0.1,
            max_tokens=120,
        )
        if isinstance(result, dict) and result.get("is_crisis"):
            return result
        return None
    except Exception as e:
        app_logger.warning(f"Crisis check failed: {e}")
        return None


def apply_guardrails(
    symptoms: List[str],
    intent: str,
    severity: Optional[float] = None,
    age: Optional[int] = None,
    temperature: Optional[float] = None,
    answers: Optional[Dict] = None,
    language: str = "en",
    chief_complaint: str = "",
) -> Tuple[Optional[Dict], str]:
    """
    Check for crisis situations only.
    Medical triage is handled by the classifier, not guardrails.
    """
    # Hard-stop for explicit severe heart/chest pain wording.
    medical_emergency_reason = _check_hardcoded_medical_emergency(chief_complaint)
    if medical_emergency_reason:
        return {
            "is_crisis": False,
            "triage_label": "Emergency",
            "confidence": 1.0,
            "reason": medical_emergency_reason,
            "action": "Call local emergency services immediately and go to the nearest emergency room now.",
        }, "hardcoded_medical_emergency"

    # Only check for mental health crisis - let the classifier handle medical triage
    crisis = check_crisis_gemini(chief_complaint, intent, symptoms)
    
    if crisis and crisis.get("is_crisis"):
        lang = language if language in CRISIS_HOTLINES else "en"
        return {
            "is_crisis": True,
            "triage_label": "Emergency",
            "confidence": 1.0,
            "reason": crisis.get("reason", "Crisis situation detected"),
            "crisis_info": CRISIS_HOTLINES[lang],
            "action": "Please reach out to a crisis helpline immediately. You are not alone.",
        }, "crisis_detected"

    # No guardrail override - let normal triage flow proceed
    return None, "none"
