from django.shortcuts import render

# Create your views here.
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .validator_engine import query_check

# api/views.py
@api_view(['POST'])
def validate_sql(request):
    raw_query = request.data.get('query', '')
    # Split by semicolon and remove empty strings
    statements = [s.strip() for s in raw_query.split(';') if s.strip()]
    
    results = []
    for stmt in statements:
        # Re-add semicolon if needed for your regex or just strip it
        res = query_check(stmt)
        results.append(res)
        
    return Response(results) # Now returns a LIST of objects


from groq import Groq
from rest_framework.response import Response
import os
from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@api_view(['POST'])
def get_sql_hint(request):
    query = request.data.get("query")
    errors = request.data.get("errors")
    
    # We use a specialized "System Prompt" to keep the AI focused
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
            model="llama-3.3-70b-versatile", # High-performance free-tier model
            messages=[{"role": "user", "content": prompt}],
        )
        return Response({"hint": completion.choices[0].message.content})
    except Exception as e:
        return Response({"hint": "AI Advisor is sleeping. Check your keywords!"}, status=500)
    
@api_view(['POST'])
def get_schema_summary(request):
    tables_info = request.data.get("tables_info")
    
    # Updated prompt for bullet points
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