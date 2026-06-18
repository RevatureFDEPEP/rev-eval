"""
Seed script for adding RAG and Context Engineering questions to the database.

This script adds questions of various types and difficulty levels for:
- RAG using Pinecone (Retrieval Augmented Generation)
- Context Engineering

The question fixtures themselves live in ``src.db.seed_data`` (a pure-data
module with no third-party imports) so they can be reused by the service's
guarded startup seeder (``src/db/seed.py``, W5-F4) without importing httpx.

Usage:
    python seed_rag_context_questions.py

Requirements:
    - Question Management Service must be running on port 8002
    - MongoDB must be accessible
"""

import asyncio
from typing import Any, Dict

import httpx

from src.db.seed_data import QUESTIONS

# Base URL for the question management service
BASE_URL = "https://automatic-system-p55wjj9v6xjcr765-8002.app.github.dev:443/v1/api"


async def create_question(question_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a single question via the API.

    Args:
        question_data: Question data dictionary

    Returns:
        Response from the API
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/questions/",
                json=question_data,
                timeout=30.0,
                follow_redirects=True
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"❌ Error creating question: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text}")
            raise


async def seed_questions():
    """
    Seed all RAG and Context Engineering questions.
    """
    print("🌱 Starting question seeding process...")
    print(f"📝 Total questions to create: {len(QUESTIONS)}\n")

    created_count = 0
    failed_count = 0

    for i, question in enumerate(QUESTIONS, start=1):
        try:
            print(f"Creating question {i}/{len(QUESTIONS)}: {question['question_text'][:60]}...")
            result = await create_question(question)
            created_count += 1
            print(f"✅ Created question ID: {result.get('_id', 'unknown')}\n")
        except Exception:
            failed_count += 1
            print(f"❌ Failed to create question {i}\n")
            continue

    print("\n" + "="*80)
    print("🎉 Question seeding completed!")
    print(f"✅ Successfully created: {created_count} questions")
    print(f"❌ Failed: {failed_count} questions")
    print("="*80)

    # Print summary by skill and difficulty
    print("\n📊 Questions by Skill:")
    rag_count = sum(1 for q in QUESTIONS if "RAG using Pinecone" in q["skills"])
    context_count = sum(1 for q in QUESTIONS if "Context Engineering" in q["skills"])
    both_count = sum(1 for q in QUESTIONS if "RAG using Pinecone" in q["skills"] and "Context Engineering" in q["skills"])
    print(f"   RAG using Pinecone: {rag_count} questions")
    print(f"   Context Engineering: {context_count} questions")
    print(f"   Both: {both_count} questions")

    print("\n📊 Questions by Difficulty:")
    for difficulty in ["easy", "medium", "hard"]:
        count = sum(1 for q in QUESTIONS if q["difficulty"] == difficulty)
        print(f"   {difficulty.capitalize()}: {count} questions")

    print("\n📊 Questions by Type:")
    for qtype in ["mcq", "multi", "true_false", "text"]:
        count = sum(1 for q in QUESTIONS if q["type"] == qtype)
        print(f"   {qtype.upper()}: {count} questions")


if __name__ == "__main__":
    asyncio.run(seed_questions())
