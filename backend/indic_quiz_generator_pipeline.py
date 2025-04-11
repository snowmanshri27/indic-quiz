import json
import json_repair
from typing import List, Dict

from haystack import Pipeline, component
from haystack.components.generators import OpenAIGenerator
from haystack.components.builders import PromptBuilder
from haystack.components.websearch.serper_dev import SerperDevWebSearch
from haystack.utils import Secret

@component
class QuizParser:
    """Parses the quiz JSON out of the LLM's response."""
    @component.output_types(quiz=Dict)
    def run(self, replies: List[str]):
        reply = replies[0]
        first_index = min(reply.find("{"), reply.find("["))
        last_index = max(reply.rfind("}"), reply.rfind("]")) + 1
        json_portion = reply[first_index:last_index]

        try:
            quiz = json.loads(json_portion)
        except json.JSONDecodeError:
            quiz = json_repair.loads(json_portion)

        if isinstance(quiz, list):
            quiz = quiz[0]

        for question in quiz.get("questions", []):
            options = question.get("options", [])
            
            # Extract label to option mapping
            label_map = {}
            for opt in options:
                if isinstance(opt, str) and len(opt) > 2 and opt[1] == '.':
                    label = opt[0].lower()
                    label_map[label] = opt
            
            # Fill in or reorder a-d
            ordered_options = []
            for label in ['a', 'b', 'c', 'd']:
                if label in label_map:
                    ordered_options.append(label_map[label])
                else:
                    ordered_options.append(f"{label}. (missing option)")

            question["options"] = ordered_options

        return quiz

def build_english_quiz_pipeline():
    pipeline = Pipeline()
    pipeline.add_component("websearch", SerperDevWebSearch(top_k=1))
    pipeline.add_component(
        "prompt_builder",
        PromptBuilder(
            template="""
            Given the following - {{text}} - in English language, create 5 multiple choice quizzes in JSON format in English language.
            
            Each question should have 4 different options, and only one of them should be correct.
            For each question, provide exactly 4 options labeled a., b., c., and d. Ensure each option is unique and plausible
            Each option should begin with a letter followed by a period and a space (e.g., "a. king").
            The question should also briefly mention the general topic of the text so that it can be understood in isolation.
            Each question should not give hints to answer the other questions.

            Respond with JSON only, no markdown or descriptions.

            Note that you are able to provide more accurate english sentences because you can understand additional context from web sources.

            Example JSON format you should absolutely follow, including the reasoning:

            {
              "quiz": {
                "topic": "a sentence explaining the topic of the text",
                "questions": [
                  {
                    "question": "text of the question",
                    "options": ["a. 1st option", "b. 2nd option", "c. 3rd option", "d. 4th option"],
                    "right_option": "c",
                    "source": "I found a source: <paste_actual_link_here> which provided the context for me to properly generate english quiz"
                  }
                ]
              }
            }

            Snippets:
            {% for doc in documents %}
            - snippet: "{{ doc.content }}"
              link: "{{ doc.meta.link or doc.meta.url or 'unknown' }}"
            {% endfor %}
            """
        ),
    )
    pipeline.add_component(
        "generator",
        OpenAIGenerator(
            api_key=Secret.from_env_var("GROQ_API_KEY"),
            api_base_url="https://api.groq.com/openai/v1",
            model="llama3-70b-8192",
            generation_kwargs={
                "max_tokens": 6000,
                "temperature": 0.5,
                "top_p": 1,
            },
        ),
    )
    pipeline.connect("websearch.documents", "prompt_builder.documents")
    pipeline.connect("prompt_builder", "generator")
    return pipeline

