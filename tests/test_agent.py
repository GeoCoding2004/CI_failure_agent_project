from tools import classify_failure_tool, parse_log_tool, suggest_fix_tool

SAMPLE_LOG = """
============================= test session starts ==============================
collected 1 item
tests/test_math.py F                                                     [100%]

=================================== FAILURES ===================================
_________________________________ test_divide __________________________________
    def test_divide():
>       assert divide(10, 0) == 5

tests/test_math.py:4: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
a = 10, b = 0
    def divide(a, b):
>       return a / b
E       ZeroDivisionError: division by zero

src/math.py:2: ZeroDivisionError
"""

def test_parse_log_tool():
    res = parse_log_tool.invoke({"log_content": SAMPLE_LOG})
    assert res["error_type"] == "ZeroDivisionError"
    assert res["file_name"] == "src/math.py"
    assert res["line_number"] == "2"

def test_classify_failure_tool():
    assert classify_failure_tool.invoke({"error_type": "ZeroDivisionError"}) == "test failure"
    assert classify_failure_tool.invoke({"error_type": "ModuleNotFoundError"}) == "dependency error"

def test_suggest_fix_tool():
    res = suggest_fix_tool.invoke({
        "error_type": "ZeroDivisionError", 
        "category": "test failure"
    })
    assert "zero" in res.lower()