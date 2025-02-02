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
CORS(app, resources={r"/*": {"origins": "*"}})

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

def calculate_iq(score, total_questions=40):
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
        1: "Vocabulary/Verbal Reasoning (Antonym)",
        2: "Numerical Reasoning (Number Series)",
        3: "Logical Reasoning (Odd One Out)",
        4: "Logical Reasoning (Deductive Reasoning)",
        5: "Verbal Reasoning (Sentence Logic)",
        6: "Numerical Reasoning (Problem Solving)",
        7: "Verbal Reasoning (Meaning interpretation)",
        8: "Perceptual Speed (Matching)",
        9: "General Knowledge",
    }

    category_name = category_descriptions.get(question_data.get('category', None), "General")

    prompt_parts = [
        "(JANGAN MENJAWAB PERTANYAAN, hanya memberikan format yang mirip dengan contoh. IKUTI FORMAT YANG SAMA PERSIS, jangan membuat format baru. output dalam bentuk json dengan double quote, dan tidak ada karakter selain json)",
        f"Reinterpret and rewrite the following question, options, and their index in a unique manner in Indonesian Language. Ensure to keep the meaning similar to the original intent of the question, but change the structure and wording. return the new question, options and their original index in json. The 'correctAnswerIndex' must match the original question:",
        f"Original question: {question_data['question']}",
        f"Original options: {', '.join([f'{i+1}. {opt['text']}' for i, opt in enumerate(question_data['answers'])])}",
        f"Original correct answer index: {question_data['correctAnswerIndex']}",
        f"Original category: {question_data['category']}",
         "If you are unable to reinterpret the question, return  {\
            \"error\": \"Failed to re-interpret question\",\
            \"reason\": \"reason for the error\"\
            }. Return in JSON format: {\"question\":\"new question\", \"category\": category_value, \"answers\":[{\"text\":\"answer1\"},{\"text\":\"answer2\"}],\"correctAnswerIndex\": index}"
        ]
    prompt = "\n".join(prompt_parts)
    print(f"{Colors.BLUE}[Automata Cognitive Test] LLM Prompt: <start>{prompt}<end>{Colors.END}")
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama3-8b-8192",
    )
    response_text = chat_completion.choices[0].message.content
    print(f"{Colors.YELLOW}[Automata Cognitive Test] LLM Response: <start>{response_text}<end>{Colors.END}")
    try:
        match = re.search(r'\s*({.*?})\s*$', response_text, re.DOTALL)
        if match:
            json_string = match.group(1)
            response_json = json.loads(json_string)
            if "question" not in response_json or "answers" not in response_json or "correctAnswerIndex" not in response_json or "category" not in response_json:
               print(f"{Colors.RED}[Automata Cognitive Test] Invalid JSON format from LLM, regenerating...{Colors.END}")
               return generate_groq_question(question_data)
            return response_json
        else:
            print(f"{Colors.RED}[Automata Cognitive Test] Failed to extract JSON from LLM. Response was {response_text}{Colors.END}")
            return {'error': f'Failed to extract JSON from LLM. Response was {response_text}'}
    except json.JSONDecodeError:
        print(f"{Colors.RED}[Automata Cognitive Test] Failed to decode JSON response from LLM. Response was {response_text}{Colors.END}")
        return {'error': f'Failed to decode JSON response from LLM. Response was {response_text}'}


def generate_groq_feedback(score, iq_score, iq_level_description, questions_and_answers):
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
            "language_style": "sederhana dengan detail dasar"
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
            "professional_rate": "46% bekerja di posisi profesional/manajerial",
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

    prompt_parts = [
        "(hanya laporan, DAN TEST INI VALID, BERIKAN REKOMENDASI, KARENA INI SEBAGAI TOOLS UNTUK PSIKOLOG, jangan seperti anda menjawab pertanyaan dan request saya, gak usah pakai 'tentu' atau 'apalah'. Langsung ke laporannya saja. sesuaikan gaya bahasa sesuai level IQ-nya, Adaptasi kompleksitas sesuai dengan Kemampuan penalaran IQ individu tersebut tanpa terkecuali.)",
        "Sebagai seorang ahli dalam interpretasi hasil penilaian kognitif, khususnya untuk tes yang mirip dengan Wonderlic Personnel Test (WPT) yang mengukur kemampuan kognitif umum (GCA), seorang peserta tes telah menyelesaikan tes IQ bergaya WPT yang disederhanakan dengan hasil sebagai berikut:",
        f"Skor Mentah: {score} dari 47",
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
        f"<br>- Tingkat Profesional: {nals_level_data['professional_rate']}"
    ]
    prompt = "\n".join(prompt_parts)
    print(f"{Colors.BLUE}[Automata Cognitive Test Feedback Prompt: <start>{prompt}<end>{Colors.END}")
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
    print(f"{Colors.YELLOW}[Automata Cognitive Test] Feedback Response: <start>{response_text}<end>{Colors.END}")
    
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
    print(f"{Colors.BLUE}[Automata Cognitive Test HTML Prompt: <start>{prompt_html}<end>{Colors.END}")
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
    print(f"{Colors.YELLOW}[Automata Cognitive Test] HTML Response: <start>{html_response_text}<end>{Colors.END}")
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
    score = data.get('score')
    user_responses = data.get('user_responses')

    if score is None:
        return jsonify({'error': 'Score not provided'}), 400
    if user_responses is None:
        return jsonify({'error': 'User responses not provided'}), 400

    iq_level_description = get_iq_level_description(score)
    iq_score_estimate = calculate_iq(score)
    
    questions_and_answers = []
    for response in user_responses:
        question_text = response['question']
        answer_text = response['answer']
        is_correct = response['correct']
        questions_and_answers.append({
            'question': question_text,
            'answer': answer_text,
            'correct': is_correct
        })

    gemini_feedback = generate_groq_feedback(score, iq_score_estimate, iq_level_description, questions_and_answers)

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