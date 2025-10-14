# app/ai_processor.py

import json
from openai import OpenAI
from .models import AiAnalysisResult

client = OpenAI() # Assumes OPENAI_API_KEY is set in environment

def extract_analysis_from_text(text: str) -> AiAnalysisResult | None:
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert at extracting structured data. Analyze the text and provide a summary and a list of all calendar events mentioned."},
                {"role": "user", "content": text}
            ],
            tools=[{
                "type": "function",
                "function": {
                    "name": "extract_document_info",
                    "description": "Extract summary and events from the document.",
                    "parameters": AiAnalysisResult.model_json_schema()
                }
            }],
            tool_choice={"type": "function", "function": {"name": "extract_document_info"}}
        )
        tool_call = response.choices[0].message.tool_calls[0]
        result_data = json.loads(tool_call.function.arguments)
        return AiAnalysisResult(**result_data)
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return None