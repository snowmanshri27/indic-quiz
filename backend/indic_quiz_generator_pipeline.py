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
        # model=Groq(id="llama3-70b-8192"),
        # model=Groq(id="meta-llama/llama-4-scout-17b-16e-instruct"),
        markdown=True
    )
    return agent


def build_quiz_prompt(chapter_text: str, num_questions: int) -> str:
    # Calculate SCQ/MCQ split
    scq_count = (num_questions + 1) // 2  # Favor SCQ if odd
    mcq_count = num_questions - scq_count

    prompt = f"""
        You are an expert quiz generator. Based on the following passage, generate a quiz in valid JSON format.

        == QUIZ STRUCTURE ==
        - The quiz must contain exactly {num_questions} total questions.
        - Of these, {scq_count} must be Single Choice Questions (SCQ) and {mcq_count} must be Multiple Choice Questions (MCQ).
        - Every question must be based solely on the passage and test a unique concept.

        == QUESTION FORMAT ==
        For each question, include:
        - "Question": the question text, starting with a word like "What", "Who", "When", "Where", "Why", or "How". Use active voice, clear grammar, and a conversational tone suitable for middle to high school students.
        - "Question_type": either "SCQ" or "MCQ"
        - "Options": exactly four plausible and unique answer choices labeled as:
        - a. ...
        - b. ...
        - c. ...
        - d. ...
        - "Right_Option":
        - For SCQ: a single lowercase letter (e.g., "a")
        - For MCQ: two or more lowercase letters **concatenated without commas or spaces** (e.g., "ac" or "abd"). Do **not** use only one correct answer for MCQ.
        - "Timer": an integer from 10 to 30, depending on difficulty

        == RULES ==
        - Output must be a valid JSON **dictionary** with the following structure:
            {{
                "Quiz": {{
                    "Topic": "...",
                    "Questions": [ ... ]
                }}
            }}
            Do not output a plain array. It must be wrapped inside the dictionary above.
        - No "all of the above" or similar options.
        - Do not include explanations, markdown, or formatting.
        - Ensure every MCQ includes more than **one correct option**.
        - Never have only one correct answer for an MCQ.
        - Every question must be logically answerable using the passage.

        == FORMAT ==
        Each question must follow this format:
        {{
            "Question": "The text of the question. If question is a MCQ, then the text (Select all answers that are correct) should follow the text of the question.",
            "Question_type": "SCQ" or "MCQ",
            "Options": ["a. ...", "b. ...", "c. ...", "d. ..."],
            "Right_Option": "a" (for SCQ) or "ac" (for MCQ),
            "Number_Of_Points_Earned": 10,
            "Chapter": "Just provide the chapter (ex: Chapter 2)",
            "Timer": 15
        }}

        == EXAMPLES ==
        {{
            "Quiz": {{
                "Topic": "The story of Kṛiṣhṇa's childhood and his encounters with various Asuras",
                "Questions": [
                    {{
                        "Question": "What was Pūtanā's task assigned by Kaṃsa?",
                        "Question_type": "SCQ",
                        "Options": ["a. To protect the newborn Kṛiṣhṇa", "b. To kill the newborn Kṛiṣhṇa", "c. To find the newborn Kṛiṣhṇa and bring him to Kaṃsa", "d. To alert the people of Gokula about Kaṃsa's plans"],
                        "Right_Option": "c",
                        "Number_Of_Points_Earned": 10,
                        "Chapter": "Chapter 16",
                        "Timer": 15
                    }},
                    {{
                        "Question": "What was the effect of Kṛiṣhṇa's kick on the cart in which Śhakaṭāsura was hiding? (Select all answers that are correct)",
                        "Question_type": "MCQ",
                        "Options": ["a. The cart was dislodged and flew away", "b. The cart was destroyed", "c. The metal jars containing milk and curd were crushed", "d. The cart's pole was shattered"],
                        "Right_Option": "abcd",
                        "Number_Of_Points_Earned": 15,
                        "Chapter": "Chapter 16",
                        "Timer": 20
                    }}
                ]
            }}
        }}

        Before finalizing the quiz, validate each question:
        - If MCQ, confirm it has 2 or more correct options.
        - If SCQ, confirm it has exactly 1 correct option.
        - If not, regenerate the question.

        Here is the story:
        \"\"\"
        {chapter_text}
        \"\"\"
    """

    return prompt