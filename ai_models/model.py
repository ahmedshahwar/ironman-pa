import json
import csv
from pathlib import Path

from setups import llm, llm_small
# ---------------------------- Read AI Prompts
PROMPT_PATHS = {
    "classification": "prompts/classification.txt",
    "daily_summary": "prompts/daily_summary.txt",
    "weekly_report": "prompts/weekly_report.txt",
}

PROMPTS = {}

for key, path in PROMPT_PATHS.items():
    try:
        with open(path, "r", encoding="utf-8") as f:
            PROMPTS[key] = f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Missing prompt file: {path}")

# ---------------------------- Initialize LLM once
llm_classification = llm_small
llm_summary = llm
# ---------------------------- AI Processing Functions
def invoke_ai(llm, prompt_template, text, last_summary=None):
    """Helper function to send formatted prompt to LLM and return JSON response."""
    if prompt_template == PROMPTS["weekly_report"] and last_summary:
        prompt = prompt_template.replace("{text}", text).replace("{last_text}", last_summary)
    else:
        prompt = prompt_template.replace("{text}", text)

    response = llm.invoke(prompt)

    if not response or not hasattr(response, "content"):
        return {"error": "Invalid response from AI", "raw_response": str(response)}

    try:
        return json.loads(response.content) if isinstance(response.content, str) else response.content
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format in AI response", "raw_response": response.content}


# ---- Classification into Categories
def classify_text(text):
    """Classifies a message/email into categories, extract tasks, generate insights."""
    response = invoke_ai(llm_classification, PROMPTS["classification"], text)
    return response


# ---- Daily Summary Generation
def generate_summary(csv_path):
    # Read data from CSV
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader, None)  # Extract headers
            data = [dict(zip(headers, row)) for row in reader]  # Convert to list of dictionaries
    except FileNotFoundError:
        return "Error: CSV file not found."
    
    # Convert data to JSON string before sending to LLM
    csv_text = json.dumps(data, indent=2)
    response = invoke_ai(llm_summary, PROMPTS["daily_summary"], csv_text)
    
    if not response or "raw_response" not in response:
        return "Error: Invalid response from AI."
    raw_response = response.get("raw_response", "")
    formatted_response = raw_response.replace("\\n", "\n").replace("\\'", "'").replace('**', '*')
    return formatted_response


# ---- Weekly Report Generation
from services.week_num import get_week_number

def generate_report(csv_path, reference_day='Monday'):
    """Generates weekly medical report from health data."""
    # Check if last week's data is available
    report_path = Path("reports")
    report_path.mkdir(exist_ok=True)

    current_week = get_week_number(reference_day, offset_weeks=1)
    prev_week = get_week_number(reference_day, offset_weeks=2)
    # current_week=8
    # prev_week=7

    curr_week_report = report_path / f"report_{current_week}.txt"
    last_week_report = report_path / f"report_{prev_week}.txt"

    prev_report = ""
    if last_week_report.exists():
        prev_report = last_week_report.read_text(encoding="utf-8").strip()

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader, None)  # Extract headers
            data = [dict(zip(headers, row)) for row in reader]  # Convert to list of dictionaries
    except FileNotFoundError:
        return "Error: CSV file not found."

    # Convert data to JSON string before sending to LLM
    csv_text = json.dumps(data, indent=2)
    response = invoke_ai(llm_summary, PROMPTS["weekly_report"], csv_text, last_summary=prev_report)
    
    if not response or "raw_response" not in response:
        return "Error: Invalid response from AI."
    raw_response = response.get("raw_response", "")
    formatted_response = raw_response.replace("\\n", "\n").replace("\\'", "'").replace('**', '*')

    # Save the new report
    new_report = formatted_response
    curr_week_report.write_text(new_report, encoding="utf-8")

    return new_report


