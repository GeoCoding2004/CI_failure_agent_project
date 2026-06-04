import argparse
import sys
import json
from agent import run_diagnostic

def main():
    parser = argparse.ArgumentParser(description="CI Failure Diagnostic Agent")
    parser.add_argument("--log", required=True, help="Path to the CI log file")
    args = parser.parse_args()

    try:
        with open(args.log, 'r') as f:
            log_content = f.read()
    except FileNotFoundError:
        print(f"Error: Log file not found at {args.log}")
        sys.exit(1)

    print("Analyzing log...")
    report = run_diagnostic(log_content)
    
    print("\n--- Diagnostic Report ---")
    print(json.dumps(report, indent=4))

if __name__ == "__main__":
    main()