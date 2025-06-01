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
                    if key.lower() not in ("question", "right_option", "question_type", "number_of_points_earned", "chapter", "source"):
                        if isinstance(value, str):
                            raw_options.append(key.strip())
                            raw_options.append(value.strip())
                # Remove those fields to clean up
                for key in list(q.keys()):
                    if key not in ("Question", "Right_Option", "Options", "Question_type", "Number_Of_Points_Earned", "Chapter", "source"):
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
        markdown=True
    )
    return agent


def build_quiz_prompt(chapter_text: str) -> str:
    prompt = f"""
        Generate 10 questions with these requirements:

        - Each question should have 4 different options, where either 1 answer or at least 2 answer choices are correct per question.
        - Exactly 5 of the questions must have exactly one correct option (Single Choice), and exactly 5 of the questions must have at least two correct options (Multiple Choice).
        - Never include "all of the above" as a possible answer choice.
        - For each question, provide exactly 4 options labeled a., b., c., and d. Ensure all options are unique and plausible.
        - Each question must test a different concept.
        - Each question should also mention the type of question it is. There are only two types: SCQ and MCQ.
        - A MCQ question has at least two right options. A SCQ question has only one right option.
        - Each question should also have the number of points associated with it. Each question is worth exactly 10 points.
        - Each question should also mention the chapter the question is from. The chapter number is mentioned at the beginning of the story.
        - Each option should begin with a letter followed by a period and a space (e.g., "a. king").
        - The question should briefly mention the general topic of the text so it can be understood in isolation.
        - Each question should not give hints to answer the other questions.

        Respond with JSON only — no markdown or extra description.

        Example JSON format you must strictly follow, including field names and structure:

        {{
        "Quiz": {{
            "Topic": "a sentence explaining the topic of the text. Don't include the type of question, number of points, or chapter number",
            "Questions": [
            {{
                "Question": "text of the question",
                "Question_type": "Type of the question: either MCQ or SCQ",
                "Options": ["a. 1st option", "b. 2nd option", "c. 3rd option", "d. 4th option"],
                "Right_Option": "c",
                "Number_Of_Points_Earned": 10,
                "Chapter": "Just provide the chapter (ex: Chapter 2)"
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