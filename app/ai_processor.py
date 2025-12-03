import json
from openai import OpenAI
from .models import AiAnalysisResult
from datetime import date # Import the date object

client = OpenAI()

# We now pass in a 'context_date'
async def extract_analysis_from_text(text: str, context_date: date) -> AiAnalysisResult | None:
    
    # 1. The new, more specific system prompt
    system_prompt = """
You are an expert academic assistant specializing in syllabus processing. Your task is to meticulously read a course syllabus, extract a concise summary, and identify all KEY, DATE-SPECIFIC events.

**Your Guiding Rules:**
1.  **Extract Events:** Focus *only* on events with a specific date, such as 'Midterm Exam', 'Final Project Due', 'Assignment 1 Deadline', or 'Spring Break'.
2.  **Ignore Recurring Events:** You MUST ignore recurring, non-graded events like 'Weekly Lecture', 'Lab Section', or 'Professor's Office Hours'.
3.  **Resolve Dates:** Use the 'Relevant Academic Year' provided in the user's message to resolve all dates. If a syllabus says 'October 10th', you must combine it with the provided year to create a full 'YYYY-MM-DD' date.
4.  **Be Precise:** Event titles should be descriptive (e.g., "Homework 1 Due," not just "Homework").
5.  **Use the Tool:** You MUST return this information *only* by using the `extract_document_info` tool. Do not respond in plain text.
"""

    # 2. The new user prompt that provides context
    user_prompt_content = f"""
Here is the context for the syllabus:
-   **Current Date:** {context_date.isoformat()}
-   **Relevant Academic Year:** {context_date.year}

Please analyze the following syllabus text based on this context.

--- START OF SYLLABUS TEXT ---
{text}
--- END OF SYLLABUS TEXT ---
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_content}
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
        
        response_message = response.choices[0].message
        
        if response_message.tool_calls:
            tool_call = response_message.tool_calls[0]
            result_data = json.loads(tool_call.function.arguments)
            # This validation step is excellent
            return AiAnalysisResult(**result_data)

    except Exception as e:
        print(f"Error calling OpenAI or processing its response: {e}")
        return None