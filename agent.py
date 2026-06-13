import json

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from tools import classify_failure_tool, parse_log_tool, suggest_fix_tool


def create_agent():
    # Initialize the Gemini 2.5 Flash model
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        temperature=0.0
    )
    
    tools = [parse_log_tool, classify_failure_tool, suggest_fix_tool]
    
    # LangGraph uses a 'state_modifier' to act as the system prompt
    system_prompt = (
        "You are an autonomous CI Diagnostic Agent. Your job is to analyze CI logs and return a diagnostic report.\n"
        "You must execute the following steps in exact sequence:\n"
        "1. Call parse_log_tool to extract the error_type, file_name, and line_number.\n"
        "2. Call classify_failure_tool passing the error_type to get the category.\n"
        "3. Call suggest_fix_tool passing the error_type and category to get a suggested fix.\n\n"
        "Format your final answer strictly as a raw JSON dictionary (no markdown blocks) with these exact keys:\n"
        "{ \"error_type\": \"...\", \"location\": \"file_name:line_number\", \"category\": \"...\", \"suggested_fix\": \"...\" }"
    )
    
    # This single line replaces the old AgentExecutor logic
    return create_react_agent(llm, tools, prompt=system_prompt)


def run_diagnostic(log_content: str) -> dict:
    agent_executor = create_agent()
    
    # LangGraph expects inputs in a standard message array format
    result = agent_executor.invoke({"messages": [("user", f"Analyze this CI log:\n\n{log_content}")]})
    
    # The final output from the agent is stored in the very last message
    final_content = result["messages"][-1].content
    
    # Extract the text safely, whether Gemini returns a string or a list of blocks
    if isinstance(final_content, list):
        output = "".join(
            block.get("text", "") for block in final_content if isinstance(block, dict)
        ).strip()
    else:
        output = final_content.strip()
        
    # Strip markdown formatting if the LLM adds it
    if output.startswith("```json"):
        output = output[7:-3].strip()
    elif output.startswith("```"):
        output = output[3:-3].strip()
        
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON", "raw_response": output}