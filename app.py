import os
import time
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from groq import Groq
import json
import random
import re

load_dotenv()

# ANSI escape codes for colors
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

app = Flask(__name__)

# Update CORS configuration for all routes
CORS(app, resources={
    r"/*": {
        "origins": ["https://wpt-iqtest.netlify.app", "http://localhost:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Add OPTIONS route handler for preflight requests
@app.route('/process_iq_test', methods=['OPTIONS'])
def handle_options():
    response = app.make_default_options_response()
    return response

iq_interpretation = {
    range(0, 13): "Umumnya untuk tenaga kerja pabrik atau kuli angkut",
    range(13, 16): "Tingkat terendah dimana tenaga kerja diminta mempelajari pekerjaan dari manual tertulis",
    range(16, 19): "Tingkat dimana tenaga kerja mampu bekerja mandiri tanpa supervisi",
    range(19, 25): "Skor rata-rata tenaga kerja yang bekerja dalam standard sistem alfa-numerik",
    range(25, 27): "Umumnya para supervisor pertama",
    range(27, 31): "Umumnya manajemen atau teknisi tingkat yang lebih tinggi",
    range(31, 51): "Umumnya para profesional dan manajer eksekutif"
}

def get_iq_level_description(score):
    for score_range, description in iq_interpretation.items():
        if score in score_range:
            return description
    return "Deskripsi level IQ tidak tersedia untuk skor ini."

def calculate_iq(score, total_questions=47):
    percentage_correct = (score / total_questions) * 100
    iq_estimate = 100

    if percentage_correct >= 90:
        iq_estimate = 140 + (percentage_correct - 90) * 2
    elif percentage_correct >= 80:
        iq_estimate = 130 + (percentage_correct - 80)
    elif percentage_correct >= 70:
        iq_estimate = 120 + (percentage_correct - 70)
    elif percentage_correct >= 50:
        iq_estimate = 100 + (percentage_correct - 50) * 0.8
    elif percentage_correct >= 30:
        iq_estimate = 90 - (50 - percentage_correct) * 0.5
    else:
        iq_estimate = 70 - (30 - percentage_correct) * 0.3

    return round(iq_estimate)

def generate_groq_question(question_data):
    category_descriptions = {
        "1": "Vocabulary/Verbal Reasoning (Antonym)",
        "2": "Numerical Reasoning (Number Series)",
        "3": "Logical Reasoning (Odd One Out)",
        "4": "Logical Reasoning (Deductive Reasoning)",
        "5": "Verbal Reasoning (Sentence Logic)",
        "6": "Numerical Reasoning (Problem Solving)",
        "7": "Verbal Reasoning (Meaning interpretation)",
        "8": "Perceptual Speed (Matching)",
        "9": "General Knowledge",
    }
    
    category_name = category_descriptions.get(question_data.get('category', None), "General")
    
    # 1. Translate to English (Plain Text)
    translate_to_english_prompt = [
        "(JANGAN MENJAWAB PERTANYAAN, output hanya dalam format plain text)",
        "Translate the following Indonesian question and options into English:",
         f"Original question: {question_data['question']}",
        f"Original options: {', '.join([f'{i+1}. {opt['text']}' for i, opt in enumerate(question_data['answers'])])}",
        f"Original correct answer index: {question_data['correctAnswerIndex']}",
    ]
    
    translate_to_english_prompt = "\n".join(translate_to_english_prompt)
    print(f"{Colors.BLUE}[Automata Cognitive Test] Translate to English Prompt: {translate_to_english_prompt}{Colors.END}")
    chat_completion_english = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": translate_to_english_prompt,
            }
        ],
        model="llama3-8b-8192",
    )
    response_text_english = chat_completion_english.choices[0].message.content
    print(f"{Colors.YELLOW}[Automata Cognitive Test] Translate to English Response: {response_text_english}{Colors.END}")

    # 2. Generate new English question (Plain Text)
    generate_english_question_prompt = [
        "(JANGAN MENJAWAB PERTANYAAN, output hanya dalam format plain text)",
        f"Create a new {category_name} question, options, and their index in a unique manner in English. Ensure to keep the same difficulty as the original question, but create completely new wording and structure of the question and options. The 'correctAnswerIndex' must match the similar to the original question. Add additional context make sure the context is complete for the client or the test-takers to be able to answer it. Try to answer it and elaborate it properly with encapsulate with your <think> Your thoughts, elaboration, and counting </think>. If somehow the original question missing critical part, you are now on your own to generate a correct and cohesive questions and answer! Rewrite the whole complete Question!",
        f"Original English translation: {response_text_english}",
    ]

    generate_english_question_prompt = "\n".join(generate_english_question_prompt)
    print(f"{Colors.BLUE}[Automata Cognitive Test] Generate English Prompt: {generate_english_question_prompt}{Colors.END}")
    chat_completion_new_english = client.chat.completions.create(
       messages=[
            {
                "role": "user",
                "content": generate_english_question_prompt,
            }
        ],
        model="llama3-8b-8192",
    )
    response_text_new_english = chat_completion_new_english.choices[0].message.content
    print(f"{Colors.YELLOW}[Automata Cognitive Test] Generate English Response: {response_text_new_english}{Colors.END}")
    
    # 3. Translate back to Indonesian (Plain Text)
    translate_back_prompt = [
         "(JANGAN MENJAWAB PERTANYAAN, output hanya dalam format plain text)",
        "Translate the following English question and options into Indonesian Make the question written and follows indonesian formal language and EYD grammar very strictly!:",
        f"Original English Generated: {response_text_new_english}",
    ]
    
    translate_back_prompt = "\n".join(translate_back_prompt)
    print(f"{Colors.BLUE}[Automata Cognitive Test] Translate Back to Indonesia Prompt: {translate_back_prompt}{Colors.END}")
    chat_completion_indonesian = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": translate_back_prompt,
            }
        ],
        model="llama3-8b-8192",
    )
    response_text_indonesian = chat_completion_indonesian.choices[0].message.content
    print(f"{Colors.YELLOW}[Automata Cognitive Test] Translate Back to Indonesia Response: {response_text_indonesian}{Colors.END}")
    
    #4. Self-Audit Question
    audit_prompt = [
        "Carefully check the following question, and answer, Try to answer it and elaborate it properly with encapsulate with your <think> Your thoughts, elaboration, and counting </think> on how you approach the problem with your logic and the available context of the question and answer. if the question is lacking complete context (Like missing number when asked number, or lacking image or figure if being asked, or Lacking correct answer selection). return <QuestionFailureFlag>TRUE</QuestionFailureFlag>. However If all Logical correct. And autocorrect some typo writingcorrectAnswerIndex is mismatched on what you have answered. Change the index based on your audit. Generate the JSON if it's still doable",
        f"Question: {response_text_indonesian}",
    ]
    audit_prompt = "\n".join(audit_prompt)
    print(f"{Colors.BLUE}[Automata Cognitive Test] Self Audit Prompt: {audit_prompt}{Colors.END}")
    chat_completion_audit = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": audit_prompt,
            }
        ],
        model="llama3-8b-8192",
    )
    audit_response = chat_completion_audit.choices[0].message.content
    print(f"{Colors.YELLOW}[Automata Cognitive Test] Self Audit Response: {audit_response}{Colors.END}")
                
    #4. Self-Audit Question
    audit_prompt = [
        "Carefully check the following question, and answer, Try to answer it and elaborate it properly with encapsulate with your <think> Your thoughts, elaboration, and counting </think> on how you approach the problem with your logic and the available context of the question and answer. if the question is lacking complete context (Like missing number when asked number, or lacking image or figure if being asked, or Lacking correct answer selection) and not logical or the answer is not correct. return <QuestionFailureFlag>. However If all Logical correct. And autocorrect some typo writingcorrectAnswerIndex is mismatched on what you have answered. Change the index based on your audit. Then Return in JSON format: {\"question\":\"translated question\", \"answers\":[{\"text\":\"answer1\"},{\"text\":\"answer2\"}],\"correctAnswerIndex\": index}",
        f"Question: {response_text_indonesian}",
    ]
    audit_prompt = "\n".join(audit_prompt)
    print(f"{Colors.BLUE}[Automata Cognitive Test] Self Audit Prompt: {audit_prompt}{Colors.END}")
    chat_completion_audit = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": audit_prompt,
            }
        ],
        model="llama3-8b-8192",
    )
    audit_response = chat_completion_audit.choices[0].message.content
    print(f"{Colors.YELLOW}[Automata Cognitive Test] Self Audit Response: {audit_response}{Colors.END}")

    if "<QuestionFailureFlag>" in audit_response:
        print(f"{Colors.RED}[Automata Cognitive Test] Self-Audit failed, returning blank JSON because <QuestionFailureFlag> was found. Response was: {audit_response}{Colors.END}")
        return {}
    else:
        # Regenerate using LLM with combined insights
        regeneration_prompt = [
            f"Original Indonesian: {response_text_indonesian}",
            f"Self-Audit Insights (Pick the correct answer from here): {audit_response}",
            "ONLY Return in JSON format: {\"question\":\"translated question\", \"answers\":[{\"text\":\"answer1\"},{\"text\":\"answer2\"}],\"correctAnswerIndex\": index}"
        ]
        regeneration_prompt = "\n".join(regeneration_prompt)
        print(f"{Colors.BLUE}[Automata Cognitive Test] Regeneration Prompt: {regeneration_prompt}{Colors.END}")

        chat_completion_regeneration = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": regeneration_prompt,
                }
            ],
            model="llama3-8b-8192",
        )
        regeneration_response = chat_completion_regeneration.choices[0].message.content
        print(f"{Colors.YELLOW}[Automata Cognitive Test] Regeneration Response: {regeneration_response}{Colors.END}")

        try:
            match_regeneration = re.search(r'\s*({.*?})\s*$', regeneration_response, re.DOTALL)
            if match_regeneration:
                json_string_regeneration = match_regeneration.group(1)
                response_json_indonesian = json.loads(json_string_regeneration)
                return response_json_indonesian
            else:
                print(f"{Colors.RED}[Automata Cognitive Test] Failed to extract JSON from LLM for Regeneration. Response was {regeneration_response}{Colors.END}")
                return {} # Return empty to trigger regeneration
        except json.JSONDecodeError:
            print(f"{Colors.RED}[Automata Cognitive Test] Failed to decode JSON response from LLM for Regeneration. Response was {regeneration_response}{Colors.END}")
            return {} # Return empty to trigger regeneration
    
def generate_groq_feedback(overall_score, iq_score, iq_level_description, questions_and_answers, category_scores):
    # Define IQ level characteristics based on NALS data
    nals_levels = {
        "Level 1 (≤225)": {
            "economic_indicators": "52% di luar angkatan kerja, 43% hidup dalam kemiskinan",
            "employment": "30% bekerja penuh waktu, median upah mingguan $240",
            "professional_rate": "5% bekerja di posisi profesional/manajerial",
            "language_style": "sederhana dan langsung"
        },
        "Level 2 (226-275)": {
            "economic_indicators": "35% di luar angkatan kerja, 23% hidup dalam kemiskinan",
            "employment": "43% bekerja penuh waktu, median upah mingguan $281",
            "professional_rate": "12% bekerja di posisi profesional/manajerial",
            "language_style": "sederhana dan langsung"
                    },
        "Level 3 (276-325)": {
            "economic_indicators": "25% di luar angkatan kerja, 12% hidup dalam kemiskinan",
            "employment": "54% bekerja penuh waktu, median upah mingguan $339",
            "professional_rate": "23% bekerja di posisi profesional/manajerial",
            "language_style": "seimbang dan informatif"
        },
        "Level 4 (326-375)": {
            "economic_indicators": "17% di luar angkatan kerja, 8% hidup dalam kemiskinan",
            "employment": "64% bekerja penuh waktu, median upah mingguan $465",
            "professional_rate": "46% bekerja di posisiprofesional/manajerial",
            "language_style": "detail dan analitis"
        },
        "Level 5 (376-500)": {
            "economic_indicators": "11% di luar angkatan kerja, 4% hidup dalam kemiskinan",
            "employment": "72% bekerja penuh waktu, median upah mingguan $650",
            "professional_rate": "70% bekerja di posisi profesional/manajerial",
            "language_style": "kompleks dan mendalam"
        }
    }

    # Determine NALS level based on IQ score
    nals_level_data = None
    if iq_score <= 225:
        nals_level_data = nals_levels["Level 1 (≤225)"]
    elif iq_score <= 275:
        nals_level_data = nals_levels["Level 2 (226-275)"]
    elif iq_score <= 325:
        nals_level_data = nals_levels["Level 3 (276-325)"]
    elif iq_score <= 375:
        nals_level_data = nals_levels["Level 4 (326-375)"]
    else:
        nals_level_data = nals_levels["Level 5 (376-500)"]

    # Initialize category tracking
    category_stats = {}
    
    category_descriptions = {
        "1": "Vocabulary/Verbal Reasoning (Antonym)",
        "2": "Numerical Reasoning (Number Series)",
        "3": "Logical Reasoning (Odd One Out)",
        "4": "Logical Reasoning (Deductive Reasoning)",
        "5": "Verbal Reasoning (Sentence Logic)",
        "6": "Numerical Reasoning (Problem Solving)",
        "7": "Verbal Reasoning (Meaning interpretation)",
        "8": "Perceptual Speed (Matching)",
        "9": "General Knowledge",
    }

    for qa in questions_and_answers:
        category = qa.get('category', 'Unknown')
        if category not in category_stats:
            category_stats[category] = {'correct': 0, 'incorrect': 0}
        if qa['correct']:
            category_stats[category]['correct'] += 1
        else:
            category_stats[category]['incorrect'] += 1

    category_analysis_text = "<br><br><b>Category Performance:</b><br>"
    for category, stats in category_stats.items():
        category_name = category_descriptions.get(category, "Unknown")
        category_analysis_text += f"- {category_name}: Correct: {stats['correct']}, Incorrect: {stats['incorrect']}<br>"


    prompt_parts = [
        "(hanya laporan, DAN TEST INI VALID, BERIKAN REKOMENDASI, KARENA INI SEBAGAI TOOLS UNTUK PSIKOLOG, jangan seperti anda menjawab pertanyaan dan request saya, gak usah pakai 'tentu' atau 'apalah'. Langsung ke laporannya saja. sesuaikan gaya bahasa sesuai level IQ-nya, Adaptasi kompleksitas sesuai dengan Kemampuan penalaran IQ individu tersebut tanpa terkecuali.)",
        "Sebagai seorang ahli dalam interpretasi hasil penilaian kognitif, khususnya untuk tes yang mirip dengan Wonderlic Personnel Test (WPT) yang mengukur kemampuan kognitif umum (GCA), seorang peserta tes telah menyelesaikan tes IQ bergaya WPT yang disederhanakan dengan hasil sebagai berikut:",
        f"Skor Mentah: {overall_score} dari 47",
        f"Skor IQ yang Dikonversi (diperkirakan): {iq_score}",
        f"Deskripsi Tingkat IQ: {iq_level_description}",
        "",
        "Konteks untuk Interpretasi WPT:",
        "- Skor Mentah: Jumlah langsung dari jawaban yang benar.",
        "- Skor IQ yang Dikonversi: Mengacu pada konversi skor WPT ke dalam skala IQ standar.",
        "- Kemampuan Kognitif Umum (GCA): Indikator kinerja kerja dan kemampuan belajar.",
        "",
        "Berdasarkan National Adult Literacy Survey (NALS):",
        "- Level 1 (≤225): Literasi dasar, 30% tingkat pekerjaan penuh waktu",
        "- Level 2 (226-275): Literasi fungsional dasar, 43% tingkat pekerjaan penuh waktu",
        "- Level 3 (276-325): Literasi menengah, 54% tingkat pekerjaan penuh waktu",
        "- Level 4 (326-375): Literasi tinggi, 64% tingkat pekerjaan penuh waktu",
        "- Level 5 (376-500): Literasi sangat tinggi, 72% tingkat pekerjaan penuh waktu",
        "",
        "Factor Demands dalam Konteks Pekerjaan:",
        "1. Pemrosesan Informasi: Kemampuan menangani dan mengolah data",
        "2. Pengambilan Keputusan dan Penalaran: Kemampuan membuat penilaian yang baik",
        "3. Interaksi Sosial: Aspek interpersonal dalam pekerjaan",
        "4. Kompleksitas Mental: Tuntutan kognitif dalam pekerjaan",
        "",
        "Buatlah laporan umpan balik yang komprehensif dan berwawasan tentang keterampilan kognitif peserta tes, mencakup:",
        "1. <b>Interpretasi Skor:</b> Analisis skor dalam konteks kemampuan kognitif",
        "2. <b>Analisis GCA:</b> Kaitan dengan potensi kinerja dan pembelajaran",
        "3. <b>Rekomendasi Strategi Kedepan:</b> Saran berbasis growth mindset sesuai level kognitif",
        "<br><br>",
        "<b>Citation:</b>",
        "1. Gottfredson, L. S. (1984). The role of intelligence and education in the division of labor.",
        "2. Kirsch, I. S., Jungeblut, A., Jenkins, L., & Kolstad, A. (1993). Adult literacy in America.",
        "3. Arvey, R. D. (1986). General ability in employment: A discussion.",
        "4. National Adult Literacy Survey (NALS) - Economic Outcomes Data",
        "<br><br>",
        "<b>Berikut adalah daftar pertanyaan dan jawaban yang diberikan oleh peserta tes:</b>",
        "<br>".join(f"{qa['question']} -> Jawaban: {qa['answer']}, Benar: {qa['correct']}" for qa in questions_and_answers),
        f"<br><br><b>NALS Level Data untuk Skor IQ {iq_score}:</b>",
        f"<br>- Indikator Ekonomi: {nals_level_data['economic_indicators']}",
        f"<br>- Pekerjaan: {nals_level_data['employment']}",
        f"<br>- Tingkat Profesional: {nals_level_data['professional_rate']}",
        category_analysis_text,
        f"<br><br><b>Category Descriptions:</b><br>" + "<br>".join(f"{key}: {value}" for key, value in category_descriptions.items())
    ]
    prompt = "\n".join(prompt_parts)
    print(f"{Colors.BLUE}[Automata Cognitive Test] Feedback Prompt: {prompt}{Colors.END}")
    # Generate content using Groq
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama3-8b-8192",  # Or another suitable model like "mixtral-8x
        # Or another suitable model like "mixtral-8x7b-32768"
    )
    response_text = chat_completion.choices[0].message.content
    print(f"{Colors.YELLOW}[Automata Cognitive Test] Feedback Response: {response_text}{Colors.END}")
    
    HTMLReformat = [
        "I have this response",
        "```",
        f"{response_text}",
        "```",
        "Make the response into HTML format and into short points with the same language",
        "Write ONLY the HTML code",
        "No spaces before title."
    ]

    prompt_html = "\n".join(HTMLReformat)
    print(f"{Colors.BLUE}[Automata Cognitive Test] HTML Prompt: {prompt_html}{Colors.END}")
    # Generate content using Groq
    response_html = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt_html,
            }
        ],
        model="llama3-8b-8192",  # Or another suitable model like "mixtral-8x7b-32768"
    )

    html_response_text = response_html.choices[0].message.content
    print(f"{Colors.YELLOW}[Automata Cognitive Test] HTML Response: {html_response_text}{Colors.END}")
    # Remove leading spaces/newlines from HTML
    cleaned_html_response = html_response_text.lstrip()
    # Return the response text
    #return response_html.choices[0].message.content
    return cleaned_html_response


@app.route('/test_llm_connection', methods=['GET'])
def test_llm_connection():
    try:
        # Use Groq client to generate content
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "This is a test.",
                }
            ],
            model="llama3-8b-8192",
        )
        response_text = chat_completion.choices[0].message.content

        if response_text:
            return jsonify({'status': 'success', 'message': 'LLM Connection Successful'})
        else:
            return jsonify({'status': 'error', 'message': 'LLM Connection Failed', 'error': 'No response text from LLM'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': 'LLM Connection Failed', 'error': str(e)})

# Store generated questions in a dictionary, indexed by their original index
generated_questions = {}
generation_percentage = 0
original_questions = []

@app.route('/get_question', methods=['POST'])
def get_question():
    global generated_questions, generation_percentage
    data = request.get_json()
    if not data or 'question_index' not in data:
        return jsonify({'error': 'Invalid request'}), 400

    question_index = data['question_index']

    if question_index not in generated_questions:
        # Generate a new question using Groq
        if question_index < len(original_questions):
            new_question_data = generate_groq_question(original_questions[question_index])
            if new_question_data:
               if 'error' in new_question_data:
                   return jsonify(new_question_data), 500
               elif not new_question_data: #Check if it returns empty json
                   return get_question() #regenerate if empty
               else:
                  generated_questions[question_index] = new_question_data
                  generation_percentage =  round((len(generated_questions) / len(original_questions)) * 100, 2)
            else:
                return jsonify({'error': f'Failed to generate question for index {question_index}'}), 500
        else:
          return jsonify({'error': 'Invalid question index'}), 400
    
    return jsonify(
        {
            'question': generated_questions[question_index],
            'generation_percentage': generation_percentage
        }
    )

@app.route('/process_iq_test', methods=['POST'])
def process_iq_test():
    data = request.get_json()
    overall_score = data.get('overall_score')
    category_scores = data.get('category_scores')
    user_responses = data.get('user_responses')


    if overall_score is None:
        return jsonify({'error': 'Overall score not provided'}), 400
    if user_responses is None:
        return jsonify({'error': 'User responses not provided'}), 400
    if category_scores is None:
         return jsonify({'error': 'Category scores not provided'}), 400

    iq_level_description = get_iq_level_description(overall_score)
    iq_score_estimate = calculate_iq(overall_score)
    
    questions_and_answers = []
    for response in user_responses:
        question_text = response['question']
        answer_text = response['answer']
        is_correct = response['correct']
        questions_and_answers.append({
            'question': question_text,
            'answer': answer_text,
            'correct': is_correct,
             'category':response.get('category', 'Unknown')
        })

    gemini_feedback = generate_groq_feedback(overall_score, iq_score_estimate, iq_level_description, questions_and_answers, category_scores)

    return jsonify({
        'iq_level_description': iq_level_description,
        'iq_score': iq_score_estimate,
        'gemini_feedback': gemini_feedback
    })

@app.route('/')
def serve_index():
    return send_file('index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_file(filename)

# Load questions from questions.json as JSON
def load_questions():
    with open('questions.json', 'r') as f:
        try:
            return json.load(f)['questions']
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in questions.json: {e}")


if __name__ == '__main__':
    try:
        original_questions = load_questions()
        app.run(debug=True, port=5001)
    except ValueError as e:
        print(f"Error loading questions: {e}")