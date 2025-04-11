# backend/test_pipeline.py

from dotenv import load_dotenv; load_dotenv()
from pprint import pprint
from indic_quiz_generator_pipeline import build_english_quiz_pipeline, QuizParser

# Create pipeline
english_quiz_generation = build_english_quiz_pipeline()

# Input
indic_topic = "The King’s Monkey Servant"
indic_text = """Moral: A king wishing long life should never keep foolish servants.”
Story: A king had a monkey as his body-guard. He was very fond of the king, and as he was very much trusted by the king, he could go into the kings’ bed room without being stopped by anyone.
Once when the king was sleeping the monkey started breezing the king with a fan. While doing this a fly came and sat on the king’s chest. The monkey tried to ward off the fly with the fan. But the fly would come again and sit on the same place.
The monkey due to its foolish nature became angry, got a sharp sword and hit the fly to kill it. The fly flew away but, the king’s chest was divided into two, and the king died."""

# Run the pipeline
english_quiz = english_quiz_generation.run(
    data={
        "websearch": {"query": f"""{indic_topic} full story text."""},
        "prompt_builder": {
            "text": indic_text
        }
    },
)

parser = QuizParser()

english_quiz_text = parser.run(replies=english_quiz['generator']['replies'])
pprint(english_quiz_text)