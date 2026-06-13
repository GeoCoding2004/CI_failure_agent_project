import argparse
import json
import sys

from agent import run_diagnostic


def main():
    parser = argparse.ArgumentParser(description="CI Failure Diagnostic Agent")
    parser.add_argument("--log", required=True, help="Path to the CI log file")
    parser.add_argument("--output", help="Path to write the JSON report to")
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

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=4)

if __name__ == "__main__":
    main()