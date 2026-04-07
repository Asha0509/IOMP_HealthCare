"""
test_triage_flow.py
-------------------
Automated tests for the clinical triage system.

Test Plan:
1. Symptom Extraction: Test if user input is correctly mapped to canonical symptoms.
2. Question Filtering: Test if follow-up questions are relevant, non-redundant, and context-aware.
3. End-to-End Triage: Simulate a full triage session and check for clinical reasoning and flow.
4. Efficiency: Measure response time for question generation and triage classification.
Each test prints the scenario, expected behavior, and actual results.
"""

import asyncio
import pytest
import time
from httpx import AsyncClient
import sys
sys.path.insert(0, './backend')
from backend.main import app
API_URL = "http://localhost:8000/api/triage"
@pytest.mark.asyncio
async def test_symptom_extraction():
    print("\nTest 1: Symptom Extraction")
    chief_complaint = "I have a bad headache and stomach ache with vomiting."
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post(f"{API_URL}/start", json={
            "chief_complaint": chief_complaint,
            "patient_age": 25,
            "patient_gender": "male",
            "language": "en"
        })
        data = resp.json()
        print("Input:", chief_complaint)
        print("Extracted Symptoms:", data.get("extracted_symptoms"))
        assert "headache" in data.get("extracted_symptoms", [])
        assert "abdominal_pain" in data.get("extracted_symptoms", [])
        assert "nausea_vomiting" in data.get("extracted_symptoms", [])

@pytest.mark.asyncio
async def test_question_filtering():
    print("\nTest 2: Question Filtering")
    chief_complaint = "I have a headache and fever."
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post(f"{API_URL}/start", json={
            "chief_complaint": chief_complaint,
            "patient_age": 30,
            "patient_gender": "female",
            "language": "en"
        })
        data = resp.json()
        print("Input:", chief_complaint)
        print("First Question:", data.get("current_question", {}))
        assert data.get("current_question", {}).get("question_text")
        # Should not ask "Do you have a headache?" or "Do you have a fever?"
        assert "headache" not in data.get("current_question", {}).get("question_text", "").lower()
        assert "fever" not in data.get("current_question", {}).get("question_text", "").lower()

@pytest.mark.asyncio
async def test_end_to_end_triage():
    print("\nTest 3: End-to-End Triage Reasoning")
    chief_complaint = "Severe chest pain radiating to my left arm and sweating."
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post(f"{API_URL}/start", json={
            "chief_complaint": chief_complaint,
            "patient_age": 55,
            "patient_gender": "male",
            "language": "en"
        })
        data = resp.json()
        session_id = data["session_id"]
        print("Input:", chief_complaint)
        print("Extracted Symptoms:", data.get("extracted_symptoms"))
        print("First Question:", data.get("current_question", {}))
        # Simulate answering all questions with 'yes' or '8' for severity
        while data.get("status") == "active":
            q = data.get("current_question", {})
            answer = "8" if q.get("answer_type") == "scale" else "yes"
            resp = await ac.post(f"{API_URL}/answer", json={
                "session_id": session_id,
                "question_id": q.get("question_id"),
                "answer": answer
            })
            data = resp.json()
        print("Final Status:", data.get("status"))
        print("Triage Label:", data.get("triage_label", "N/A"))
        assert data.get("status") == "completed"

@pytest.mark.asyncio
async def test_efficiency():
    print("\nTest 4: Efficiency (Response Time)")
    chief_complaint = "I have a cough and fever."
    async with AsyncClient(app=app, base_url="http://test") as ac:
        start = time.time()
        resp = await ac.post(f"{API_URL}/start", json={
            "chief_complaint": chief_complaint,
            "patient_age": 40,
            "patient_gender": "female",
            "language": "en"
        })
        elapsed = time.time() - start
        print("Input:", chief_complaint)
        print("Response Time (s):", elapsed)
        assert elapsed < 2.5  # Should be fast for local dev


@pytest.mark.asyncio
async def test_hardcoded_intense_heart_ache_emergency_short_circuit():
    print("\nTest 5: Hardcoded emergency short-circuit (intense heart ache)")
    chief_complaint = "I have intense heart ache since this morning"
    async with AsyncClient(app=app, base_url="http://test") as ac:
        start_resp = await ac.post(f"{API_URL}/start", json={
            "chief_complaint": chief_complaint,
            "patient_age": 49,
            "patient_gender": "male",
            "language": "en"
        })
        start_data = start_resp.json()

        print("Input:", chief_complaint)
        print("Start status:", start_data.get("status"))
        print("Guardrail message:", start_data.get("message"))

        assert start_data.get("status") == "completed"
        assert "emergency" in (start_data.get("message") or "").lower() or "cardiac" in (start_data.get("message") or "").lower()

        session_id = start_data.get("session_id")
        result_resp = await ac.get(f"{API_URL}/result/{session_id}")
        result_data = result_resp.json()

        print("Result triage label:", result_data.get("triage_label"))
        assert result_data.get("triage_label") == "Emergency"

if __name__ == "__main__":
    asyncio.run(test_symptom_extraction())
    asyncio.run(test_question_filtering())
    asyncio.run(test_end_to_end_triage())
    asyncio.run(test_efficiency())
    asyncio.run(test_hardcoded_intense_heart_ache_emergency_short_circuit())
