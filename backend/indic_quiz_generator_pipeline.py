# backend/indic_quiz_generator_pipeline.py

import json
import json_repair
from agno.agent import Agent
from agno.models.groq import Groq

class QuizParser:
    """Parses the quiz JSON out of the LLM's response."""

    def run(self, reply_text: str):
        import re

        # Extract JSON-ish content
        first_index = min(reply_text.find("{"), reply_text.find("["))
        last_index = max(reply_text.rfind("}"), reply_text.rfind("]")) + 1
        json_portion = reply_text[first_index:last_index]

        try:
            quiz = json.loads(json_portion)
        except json.JSONDecodeError:
            quiz = json_repair.loads(json_portion)

        # 🔽 NEW: Handle if `quiz` is a string after decoding (bad LLM output)
        if isinstance(quiz, str):
            try:
                quiz = json.loads(quiz)
            except json.JSONDecodeError:
                quiz = json_repair.loads(quiz)

        # 🔽 Support the new JSON format
        if "Quiz" in quiz:
            quiz = quiz["Quiz"]

        questions = quiz.get("Questions") or quiz.get("questions", [])


        for q in questions:
            raw_options = q.get("Options") or q.get("options")

            # Handle if options is a dictionary (malformed JSON case)
            if isinstance(raw_options, dict):
                raw_options = list(raw_options.values())
            elif not isinstance(raw_options, list):
                # Attempt to reconstruct options from key-value pairs
                raw_options = []
                for key, value in q.items():
                    if key.lower() not in ("question", "right_option", "options", "question_type", "number_of_points_earned", "chapter", "timer", ):
                        if isinstance(value, str):
                            raw_options.append(key.strip())
                            raw_options.append(value.strip())
                # Remove those fields to clean up
                for key in list(q.keys()):
                    if key.lower() not in ("question", "right_option", "options", "question_type", "number_of_points_earned", "chapter", "timer", ):
                        q.pop(key)

            if not isinstance(raw_options, list):
                raw_options = []

            # Normalize options
            normalized = []
            seen = set()
            for opt in raw_options:
                if not isinstance(opt, str):
                    continue
                match = re.match(r"^[a-dA-D]\.\s+(.*)", opt.strip())
                text = match.group(1).strip() if match else opt.strip()
                if text not in seen:
                    seen.add(text)
                    normalized.append(text)

            while len(normalized) < 4:
                normalized.append("(missing option)")

            normalized = normalized[:4]
            labeled = [f"{label}. {text}" for label, text in zip("abcd", normalized)]
            q["Options"] = labeled

        quiz["Questions"] = questions

        return quiz


def build_english_quiz_agent():
    agent = Agent(
        model=Groq(id="llama-3.3-70b-versatile"),
        # model=Groq(id="meta-llama/llama-4-scout-17b-16e-instruct"),
        markdown=True
    )
    return agent


def build_quiz_prompt(chapter_text: str, num_questions: int) -> str:
    # Calculate SCQ/MCQ split
    scq_count = (num_questions + 1) // 2  # Favor SCQ if odd
    mcq_count = num_questions - scq_count

    prompt = f"""
        Generate questions with these requirements:

        - There should be exactly {num_questions} questions with exactly {scq_count} Single Choice Questions (SCQ) and {mcq_count} Multiple Choice Questions (MCQ).
        - For each question, provide exactly 4 answer options labeled a., b., c., and d. Ensure all options are unique and plausible.
        - Never include "all of the above" as a possible option.
        - Each option should begin with a letter followed by a period and a space (e.g., "a. king").
        - Each question must test a different concept.
        - Each question should also mention the type of question it is. There are only two types: SCQ and MCQ.
        - A SCQ (single choice question) must have only one right option.
        - A MCQ (multiple choice question) must have at least two right options. 
        – Each question must be focussed solely on the passage. 
        - Each question should have a time, between 10 to 30 seconds, associated with answering the question, dependent on the difficulty of the question.
        - Each question should use active voice and make it more direct and natural-sounding.
        - Each question should be constructuved like "What" or "Who" or "Where" or "When" or "How" or "Why" and so on.
        – Each question must be phrased conversationally and directly, avoiding awkward or overly formal constructions.
        – Each question should be grammatically correct and suitable for middle to high school readers.
        - The final output must be a valid JSON array with no syntax errors, no markdown or extra description.

        Example JSON format you must strictly follow, including field names and structure:

        {{
        "Quiz": {{
            "Topic": "a sentence explaining the topic of the text. Don't include the type of question, number of points, or chapter number",
            "Questions": [
            {{
                "Question": "only the text of the question, do not mention type, number of points earned, or time to answer. If question is a MCQ, then the text "(Select all answers that are correct)" should follow the question",
                "Question_type": "Type of the question: either MCQ or SCQ",
                "Options": ["a. 1st option", "b. 2nd option", "c. 3rd option", "d. 4th option"],
                "Right_Option": "c",
                "Number_Of_Points_Earned": 10,
                "Chapter": "Just provide the chapter (ex: Chapter 2)"
                "Timer": "Include number of seconds for question (ex: 10)"
            }}
            ]
        }}
        }}

        Here is the story:
        \"\"\"
        {chapter_text}
        \"\"\"
    """

    return prompt