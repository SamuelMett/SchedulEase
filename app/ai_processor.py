import json
from openai import OpenAI
from .models import AiAnalysisResult

client = OpenAI()

def extract_analysis_from_text(text: str) -> AiAnalysisResult | None:
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                # A more forceful system prompt to ensure tool use
                {"role": "system", "content": "You are a highly intelligent data extraction assistant. Your sole purpose is to analyze the user's text and extract a summary and a list of calendar events. You MUST use the `extract_document_info` function to return the data in the required structured format."},
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
        
        response_message = response.choices[0].message
        
        if response_message.tool_calls:
            tool_call = response_message.tool_calls[0]
            result_data = json.loads(tool_call.function.arguments)
            return AiAnalysisResult(**result_data)
        else:
            # The model did not use the tool, log its response for debugging
            print("--- AI did not use the tool. Response content: ---")
            print(response_message.content)
            print("-------------------------------------------------")
            return None

    except Exception as e:
        print(f"Error calling OpenAI or processing its response: {e}")
        return None