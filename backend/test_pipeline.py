# backend/test_pipeline_agno.py

from dotenv import load_dotenv; load_dotenv()
from pprint import pprint
from indic_quiz_generator_pipeline import build_english_quiz_agent, build_quiz_prompt, QuizParser

# Input
chapter_text = """
    Chapter 1

    Sanatana Dharma explains the three primary forms of Bhagavān (भगवान्) as Brahma Deva (ब्रह्म-देव) - the creator, Viṣhṇu Bhagavān (विष्णु-भगवान्) - the preserver, and Shiva Bhagavān (शिव-भगवान्) - the destroyer.

    Srimad-Bhāgavatam (श्रीमद्-भागवतम्) is the authoritative source that speaks about Viṣhṇu Bhagavān. 

    The Dashāvatāra (दशावतार) is an excerpt from Srimad-Bhāgavatam that speaks about the ten primary Avatāras of Viṣhṇu. Dasha (दश) means ten and Avatāra (अवतार) means incarnation.

    Throughout the history of the universe, Bhagavān Viṣhṇu has incarnated in various forms for upholding Dharma (धर्म) and eradicating Adharma (अधर्म). The knowledge of these Avatāras is fundamentally important in understanding and appreciating bharatīya samskriti (भारतीय-संस्कृति). And they are fun.

    From incarnating as a fish in Matsya-Avatāra (मत्स्य-अवतार), to the incarnation as a perfect human being in Rama Avatāra (राम-अवतार), Bhagavān Viṣhṇu teaches us immense lessons in morality and virtue. A better way of saying it, is that they teach us Dharma. They offer us a grounding knowledge of the vastness that is Bhāratam. And most of all, brings a sense of Bhakti (भक्ति) into our lives.

    Over the course of my life learning and teaching Sanātana Dharma (सनातन-धर्म), I’ve come across several people who have asked for a crash course in Hinduism. While it is impossible to fit the vastness of our culture into a synopsis, if there ever is a shortest, fastest path to understanding Sanātana Dharma, it is through the Dashāvatāra. 

    The ten Avatāras are listed below.
    Matsya Avatāra - मत्स्य-अवतार
    Viṣhṇu Bhagavān incarnates as a fish to save the sapta-rishis (सप्तऋषि), Vedas (वेद), and the seeds of various plants and herbs. He helps King Satyavrata (सत्यव्रत) to transport all of them to safety - to the beginning of the next Manvantara (मन्वन्तर).
    Kūrma Avatāra - कूरम-अवतार
    (Bhagavān Viṣhṇu incarnates as a huge turtle to hold the mountain Mandara (मन्दर) on his back and help Devas and Asuras churn the milky ocean to get amrta (अमृत) - a nectar that is said to give everlasting life.
    Varāha Avatāra - वराह-अवतार
    Hiraṇyākṣha (हिरण्याक्ष), an asura of the underworld, took Bhūmī-devī (भूमी-देवी) - Mother earth, to his place of abode. This place, called Rasātala (रसातल) was under the cosmic ocean. Bhagavān Viṣhṇu incarnated as a big boar and brought back Mother Earth.
    Narasimha Avatāra - नरसिंह-अवतार
    Bhagavān incarnates as a half man-half lion to protect his devotee, Prahlāda (प्रह्लाद) - a 5-year-old boy, who had staunch devotion towards Bhagavān Viṣhṇu.
    Vāmana Avatāra - वामन-अवतार
    When Mahābalī (महाबली), the grandson of Prahlada had conquered all the 3 worlds, Bhagavān comes as a small dwarf - Vāmana, and frees the worlds from Mahābalī’s atrocities.
    Paraśhurāma Avatāra - परशुराम-अवतार
    Bhagavān comes as Paraśhurāma to punish the Kings who had forgotten their dharma and started bothering Sādhus.
    Shri Rāma Avatāra - श्रीराम-अवतार
    A divine Avatāra to give the world a perfect role model. To show the importance of obedience to parents’ words. And also, to demonstrate how to treat joy and sorrow as equal.
    Balarāma Avatāra - बलराम-अवतार
    Born as Kṛiṣhṇa’s elder brother, Balarāma helped Kṛiṣhṇa fight adharma and protect Sādhus.
    Sri Krishna Avatāra - श्रीकृष्ण-अवतार
    The sweetest Avatāra of Bhagavān, who incarnated to shower his divine leelās (लीला) on people, so that we can sing his name, and remember his beauty. Not to mention, the pranks that he played on gopikās (गोपिका) and gopas (गोप) of the village.
    Kalki Avatāra - कल्कि-अवतार
    This Avatāra is going to happen at the end of the Kali-Yuga (कलियुग), when people would forget all dharma and start to lead a completely adharmic life.

    The Dashāvatāra stories are fun. They are inspiring. They teach us Dharma. They teach us about Bhāratam. We dedicate the telling of this series to every single one of us, who aspire to reach Bhagavān Viṣhṇu himself, one day.

    A brief background about Bhāgavatam

    Srimad-Bhāgavatam (श्रीमद्-भागवतम्) is a mahā purāṇa with 10 unique characteristics 
    Sarga (सर्ग) - Primary Creation 
    Visarga (विसर्ग) - Secondary Creation
    Sthānam (स्थान) - How Bhagavān keeps everything under control
    Poṣhaṇam (पोषण) - How Bhagavān nourishes all jīvas
    ūtayas (ऊतयः) - vāsanās, latent tendencies
    Manvantara (मन्वन्तर) - Stories of 14 Manus
    Iśhā anukathā (ईशा अनुकथा) - Various Avatāras of Bhagavān
    Nirodha (निरोध) - When Bhagavān does yoga nidra (During prayalam), jeevas reside inside Him
    Mukti (मुक्ति) - Attaining Bhagavān’s charanam, leaving ahaṅkāra (अहङ्कार) - the feeling of (I) and mamakāra (ममकार) - the feeling of mine
    Āśhraya (आश्रय) - Taking refuge in Bhagavān’s charanam

    Srimad-Bhāgavatam (श्रीमद्-भागवतम्) has 12 Skandās (Cantos), 335 chapters and 18,000 shlokas. All 12 Skandās describe the glories of Bhagavān, greatness of bhagavataḥ nāmasaṅkīrtanam and are filled with charitras (stories) of the devotees of Bhagavān.
    """

final_prompt = build_quiz_prompt(chapter_text)

english_quiz_agent = build_english_quiz_agent()

# Get the response
response = english_quiz_agent.run(final_prompt)

parser = QuizParser()

english_quiz_text = parser.run(response.content)
pprint(english_quiz_text)