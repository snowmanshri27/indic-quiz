# backend/gradio_ui.py
import sys
import os

# 👇 Add parent directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import gradio as gr
from backend.indic_quiz_generator_pipeline import build_english_quiz_pipeline, QuizParser
from dotenv import load_dotenv; load_dotenv()

english_quiz_generation = build_english_quiz_pipeline()
parser = QuizParser()

quiz_data = {"questions": [], "index": 0, "answers": [], "last_selected": None}

def generate_quiz(topic, story):
    try:
        english_quiz = english_quiz_generation.run(
            data={
                "websearch": {"query": topic},
                "prompt_builder": {
                    "text": story
                }
            },
        )
    except Exception as e:
        return (
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(value=f"Error: {str(e)}"),
            gr.update(choices=[], value=None),
            gr.update(value=""),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    english_quiz_text = parser.run(replies=english_quiz['generator']['replies'])
    quiz_data["questions"] = english_quiz_text["quiz"]["questions"]
    quiz_data["index"] = 0
    quiz_data["answers"] = []
    quiz_data["last_selected"] = None

    return (
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(value=f"**Question 1 of {len(quiz_data['questions'])}:**\n" + quiz_data["questions"][0]["question"]),
        gr.update(choices=quiz_data["questions"][0]["options"], value=None, interactive=True),
        gr.update(value=""),
        gr.update(visible=False),
        gr.update(visible=True)
    )

def render_question(index):
    q = quiz_data["questions"][index]
    question = f"**Question {index+1} of {len(quiz_data['questions'])}:**\n" + q["question"]
    options = q["options"]
    quiz_data["last_selected"] = None
    return (
        gr.update(value=question),  # question_text
        gr.update(choices=options, value=None, interactive=True),  # options
        gr.update(value="")  # feedback_text
    )

def submit_answer(option):
    if option is None:
        return gr.update(), "⚠️ Please select an option. Or, flip to reveal the answer.", gr.update(visible=False)

    quiz_data["last_selected"] = option
    current_q = quiz_data["questions"][quiz_data["index"]]
    correct = current_q["right_option"]
    selected_letter = option[0].lower()
    correct_letter = correct.lower()

    if selected_letter == correct_letter:
        feedback = f"✅ Correct! The answer is: {option}"
    else:
        feedback = f"❌ Incorrect. You chose: {option}"

    return gr.update(interactive=False), feedback, gr.update(visible=True)  # Flip button now shows again only after answer


def flip_to_show_answer():
    current_q = quiz_data["questions"][quiz_data["index"]]
    correct_letter = current_q["right_option"].lower()
    correct_option_text = next(
        (opt for opt in current_q["options"] if opt.lower().startswith(correct_letter)), "Unknown"
    )
    return gr.update(value=f"✅ Correct answer: {correct_option_text}")

def next_question():
    quiz_data["index"] += 1
    if quiz_data["index"] >= len(quiz_data["questions"]):
        return (
            gr.update(visible=True),   # Show input_form
            gr.update(visible=False),  # Hide flashcard
            gr.update(value="Quiz complete! Go back to the story input to generate a new quiz."),
            gr.update(choices=[], value=None),
            gr.update(value=""),
            gr.update(visible=False),
            gr.update(visible=False)
        )
    
    # Quiz is not over yet → render next question
    return (
        gr.update(visible=False),  # input_form hidden
        gr.update(visible=True),   # flashcard visible
    ) + render_question(quiz_data["index"]) + (
        gr.update(visible=False),  # hide flip btn
        gr.update(visible=True)    # show next btn
    )

def go_back():
    # Reset all state variables and UI components
    quiz_data["questions"] = []
    quiz_data["index"] = 0
    quiz_data["answers"] = []
    quiz_data["last_selected"] = None

    return (
        gr.update(visible=True),   # Show input form
        gr.update(visible=False),  # Hide flashcard section
        gr.update(value=""),       # Clear question
        gr.update(choices=[], value=None),  # Clear options
        gr.update(value=""),       # Clear feedback
        gr.update(visible=False),  # Hide flip button
        gr.update(visible=True)    # Ensure next button is visible (it will be reused)
    )


with gr.Blocks() as demo:
    with gr.Column(visible=True) as input_form:
        topic_input = gr.Textbox(label="Enter quiz topic", placeholder="e.g. The King’s Monkey Servant")
        story_input = gr.Textbox(label="Enter a story", lines=10)
        submit_btn = gr.Button("Generate Quiz")

    with gr.Column(visible=False) as flashcard:
        question_text = gr.Markdown()
        options = gr.Radio(choices=[], label="Select an option", interactive=True)
        feedback_text = gr.Markdown()
        flip_btn = gr.Button("Flip to show answer", visible=False)
        next_btn = gr.Button("Next Question", visible=True)
        back_btn = gr.Button("Go back to story input", visible=True)

    submit_btn.click(
        generate_quiz,
        inputs=[topic_input, story_input],
        outputs=[input_form, flashcard, question_text, options, feedback_text, flip_btn, next_btn]
    )
    options.change(
        submit_answer,
        inputs=options,
        outputs=[options, feedback_text, flip_btn]
    )
    flip_btn.click(flip_to_show_answer, outputs=feedback_text)
    next_btn.click(
        next_question,
        outputs=[input_form, flashcard, question_text, options, feedback_text, flip_btn, next_btn]
    )
    back_btn.click(go_back, outputs=[input_form, flashcard, question_text, options, feedback_text, flip_btn, next_btn])


if __name__ == "__main__":
    demo.launch(share=True)
