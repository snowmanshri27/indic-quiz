# backend/gurukula_quizgen.py
# -*- coding: utf-8 -*-

import os
import re
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from dotenv import load_dotenv; load_dotenv()
from config import env_config, app_config
from indic_quiz_generator_pipeline import (
    build_english_quiz_agent,
    build_quiz_prompt,
    QuizParser
)
from utils.gsheets import clear_all_sheet_formatting_only

SERVICE_ACCOUNT_FILE = env_config["SERVICE_ACCOUNT_FILE"]
GOOGLE_SCOPES = env_config["GOOGLE_SCOPES"]
SPREADSHEET_NAME = app_config["spreadsheet"]["name"]

# ======== STEP 1: Run Agent and Get JSON ========
def generate_quiz_json(chapter_text: str, num_questions: int = 15) -> dict:
    prompt = build_quiz_prompt(chapter_text, num_questions)
    agent = build_english_quiz_agent()
    response = agent.run(prompt)
    parsed_quiz = QuizParser().run(response.content)
    return parsed_quiz

# ======== STEP 2: Convert to DataFrame ========
def clean_option(opt: str) -> str:
    return re.sub(r'^[a-d]\.\s*', '', opt.strip(), flags=re.IGNORECASE)

def quiz_json_to_dataframe(quiz_json: dict) -> pd.DataFrame:
    questions = quiz_json['Questions']
    return pd.DataFrame(
        {
            "Chapter": q["Chapter"],
            "Timer": q["Timer"],
            "Points": q["Number_Of_Points_Earned"],
            "Type": q["Question_type"],
            "Question": q["Question"].strip() + "?" if not q["Question"].strip().endswith("?") else q["Question"].strip(),
            "Option A": clean_option(q["Options"][0]) if len(q["Options"]) > 0 else "",
            "Option B": clean_option(q["Options"][1]) if len(q["Options"]) > 1 else "",
            "Option C": clean_option(q["Options"][2]) if len(q["Options"]) > 2 else "",
            "Option D": clean_option(q["Options"][3]) if len(q["Options"]) > 3 else "",
            "Right Answer": q["Right_Option"]
        }
        for q in questions
    )

# ======== STEP 3: Upload to Google Sheet ========
def upload_to_sheet(df: pd.DataFrame, chapter_title: str):
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=GOOGLE_SCOPES)
    client = gspread.authorize(creds)

    spreadsheet = client.open(SPREADSHEET_NAME)
    
    # Check if sheet with chapter_title exists, else create it
    try:
        worksheet = spreadsheet.worksheet(chapter_title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=chapter_title, rows=100, cols=20)

    worksheet.clear()

    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

    print("✅ Google Sheet updated.")

    return spreadsheet.id, creds

# ======== STEP 4: Conditional Formatting ========
def apply_conditional_formatting(spreadsheet_id: str, chapter_title:str, df: pd.DataFrame, creds):
    sheets_api = build('sheets', 'v4', credentials=creds)
    sheet_metadata = sheets_api.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = None
    for s in sheet_metadata['sheets']:
        if s['properties']['title'] == chapter_title:
            sheet_id = s['properties']['sheetId']
            break

    if sheet_id is None:
        raise ValueError(f"Sheet ID not found for worksheet '{chapter_title}'")

    # clear all existing color formatting
    clear_all_sheet_formatting_only(sheets_api, spreadsheet_id, sheet_id)

    option_columns = {'a': 5, 'b': 6, 'c': 7, 'd': 8}  # F-I
    highlight_color = {"red": 0.78, "green": 0.90, "blue": 0.79}
    requests = []

    for i, row in enumerate(df.itertuples(index=False), start=1):  # +1 to skip header
        right_answer = str(row[-1]).lower()
        for letter, col_idx in option_columns.items():
            cell_format = {
                "userEnteredFormat": {
                    "backgroundColor": highlight_color if letter in right_answer else None
                }
            }
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": i,
                        "endRowIndex": i + 1,
                        "startColumnIndex": col_idx,
                        "endColumnIndex": col_idx + 1
                    },
                    "cell": cell_format,
                    "fields": "userEnteredFormat.backgroundColor"
                }
            })

    if requests:
        sheets_api.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()

    print("✅ Correct options highlighted in green.")

# ======== MAIN PIPELINE FUNCTION ========
def run_gurukula_quiz_pipeline(chapter_text: str, chapter_title: str, ):
    # get the chapter counts from the app_config YAML
    num_questions = app_config.get("chapter_question_counts", {}).get(chapter_title, 15)  # fallback to 15
    quiz_json = generate_quiz_json(chapter_text, num_questions)
    df = quiz_json_to_dataframe(quiz_json)
    spreadsheet_id, creds = upload_to_sheet(df, chapter_title)
    apply_conditional_formatting(spreadsheet_id, chapter_title, df, creds)


# Optional: Enable CLI use
if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) != 2:
        print("Usage: python backend/gurukula_quizgen.py <path_to_chapter_text.txt>")
    else:
        chapter_file = Path(sys.argv[1])
        if not chapter_file.exists():
            print(f"❌ File not found: {chapter_file}")
        else:
            chapter_path = sys.argv[1]
            # Get the file name without directory and extension
            chapter_title = (
                os.path.splitext(os.path.basename(chapter_path))[0]
            )
            chapter_text = chapter_file.read_text()
            run_gurukula_quiz_pipeline(chapter_text, chapter_title)
