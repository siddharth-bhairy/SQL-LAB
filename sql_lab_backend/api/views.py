from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .validator_engine import query_check

from groq import Groq
import os
from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ── Validate ──────────────────────────────────────────────────────────────────

@api_view(['POST'])
def validate_sql(request):
    raw_query = request.data.get('query', '').strip()

    if not raw_query:
        return Response({"errors": ["Empty query."]})

    # Split on semicolons, drop empty fragments
    statements = [s.strip() for s in raw_query.split(';') if s.strip()]

    if len(statements) == 1:
        # ✅ Single statement — return a plain object so the frontend
        # can read data.type / data.errors directly (NOT wrapped in a list)
        return Response(query_check(statements[0]))

    # Multiple statements — validate all; bail on first error
    results = []
    for stmt in statements:
        res = query_check(stmt)
        if 'errors' in res:
            # Surface the failing statement so the frontend can show it
            res['failedStatement'] = stmt
            return Response(res)
        results.append(res)

    # All valid — return under a known key so frontend can handle it
    return Response({"type": "multi", "results": results})


# ── AI Hint ───────────────────────────────────────────────────────────────────

@api_view(['POST'])
def get_sql_hint(request):
    query  = request.data.get("query")
    errors = request.data.get("errors")

    prompt = f"""
    The user wrote this invalid SQL: "{query}"
    The technical errors are: {errors}

    Provide a concise 1-sentence explanation of what is wrong and then provide the corrected SQL query.
    Format your response exactly like this:
    Hint: <Explanation>
    Fix: <Corrected SQL>
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
        )
        return Response({"hint": completion.choices[0].message.content})
    except Exception as e:
        return Response({"hint": "AI Advisor is sleeping. Check your keywords!"}, status=500)


# ── Schema Summary ────────────────────────────────────────────────────────────

@api_view(['POST'])
def get_schema_summary(request):
    tables_info = request.data.get("tables_info")

    prompt = f"""
    You are a Senior Database Architect.
    Summarize the following database schema using 3-4 short bullet points:
    {tables_info}

    Focus on:
    - What the system represents.
    - The primary entities.
    - The relationships and cardinality between them.

    Use a '-' for each bullet point. Do not provide SQL code.
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
        )
        return Response({"summary": completion.choices[0].message.content})
    except Exception as e:
        return Response({"summary": "• Could not generate summary."}, status=500)