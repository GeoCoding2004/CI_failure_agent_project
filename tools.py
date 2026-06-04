import re
from langchain_core.tools import tool

@tool
def parse_log_tool(log_content: str) -> dict:
    """Extracts error type, file name, and line number from a raw CI log string using regex."""
    # Look for the error type (e.g., "E       ZeroDivisionError: ...")
    error_type_match = re.search(r'E\s+([A-Za-z0-9_]+Error):', log_content)
    error_type = error_type_match.group(1) if error_type_match else "UnknownError"
    
    # Use findall to get a list of ALL file:line matches in the log
    traceback_matches = re.findall(r'^([a-zA-Z0-9_./-]+):(\d+)', log_content, re.MULTILINE)
    
    # Grab the very last match in the list, which represents the root cause of the crash
    if traceback_matches:
        file_name, line_number = traceback_matches[-1] 
    else:
        file_name, line_number = "UnknownFile", "UnknownLine"

    return {
        "error_type": error_type,
        "file_name": file_name,
        "line_number": line_number
    }

@tool
def classify_failure_tool(error_type: str) -> str:
    """Classifies the failure into a category based on the error type."""
    error_type_lower = error_type.lower()
    if "module" in error_type_lower or "import" in error_type_lower:
        return "dependency error"
    elif "timeout" in error_type_lower:
        return "timeout"
    elif "syntax" in error_type_lower or "indentation" in error_type_lower:
        return "build error"
    else:
        return "test failure"

@tool
def suggest_fix_tool(error_type: str, category: str) -> str:
    """Returns a suggested fix as a string given the error type and category."""
    if error_type == "ZeroDivisionError":
        return "Add a conditional check to ensure the denominator is not zero before dividing."
    if category == "dependency error":
        return "Verify that the required module is listed in requirements.txt and installed in the CI environment."
    if category == "build error":
        return "Review the code for syntax typos or missing brackets around the failed line."
    return "Review the failing assertion inputs and ensure edge cases are handled properly."