# backend/gradio_ui.py
import sys
import os

# 👇 Add parent directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import gradio as gr
from backend.indic_quiz_generator_pipeline import build_english_quiz_pipeline, QuizParser
from dotenv import load_dotenv

load_dotenv()

parser = QuizParser()
english_quiz_generation_pipeline = build_english_quiz_pipeline()

def generate_quiz_ui(topic, story):
    generated_quiz = english_quiz_generation_pipeline.run(
        data={
            "websearch": {"query": f"""{topic} full story text."""},
            "prompt_builder": {
                "text": story
            }
        },
    )

    english_quiz_text = parser.run(replies=generated_quiz['generator']['replies'])

    return english_quiz_text

demo = gr.Interface(
    fn=generate_quiz_ui,
    inputs=[
        gr.Textbox(label="Topic", placeholder="e.g. The King’s Monkey Servant"),
        gr.Textbox(label="Story Text", lines=10, placeholder="Paste your story here..."),
    ],
    outputs="textbox",
    title="Indic Quiz Generator",
    description="Enter a story and topic to generate English quiz cards using LLM",
)

if __name__ == "__main__":
    demo.launch(share=True)
