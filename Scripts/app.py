from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from pydub import AudioSegment
from google.cloud import speech
import os
import io

# Carregar variáveis de ambiente do arquivo .env
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '../APIKey/Api.json'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['ALLOWED_EXTENSIONS'] = {'wav', 'mp3', 'ogg', 'opus'}
app.secret_key = 'NDPA98@D3HA#@6789%@IU3DO2837DG23I78auyvdauedvQ38D7Q3Udae'

# Verificar se as pastas existem e criá-las se não existirem
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

if not os.path.exists(app.config['OUTPUT_FOLDER']):
    os.makedirs(app.config['OUTPUT_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def convert_to_wav(file_path):
    try:
        audio = AudioSegment.from_file(file_path)
        # Converter para mono
        audio = audio.set_channels(1)
        # Exportar o áudio como 16 bits por amostra
        wav_path = file_path.rsplit('.', 1)[0] + '.wav'
        audio.export(wav_path, format='wav', parameters=["-acodec", "pcm_s16le"])
        print(f"Arquivo convertido para WAV: {wav_path}")
        return wav_path
    except Exception as e:
        print(f"Erro ao converter arquivo para WAV: {e}")
        return None

def transcribe_audio(audio_file):
    try:
        client = speech.SpeechClient()
        with io.open(audio_file, 'rb') as f:
            content = f.read()

        print(f"Conteúdo do áudio: {content[:100]}... (truncated)")

        audio = speech.RecognitionAudio(content=content)

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=48000,
            language_code="pt-BR",
        )

        response = client.recognize(config=config, audio=audio)

        transcripts = [result.alternatives[0].transcript for result in response.results]
        print(f"Transcrição: {transcripts}")
        return transcripts
    except Exception as e:
        print(f"Erro ao transcrever áudio: {e}")
        return []

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == "POST":
        if 'file' not in request.files:
            flash('No file uploaded!')
            return redirect(request.url)
        
        file = request.files['file']

        if file.filename == '':
            flash('No file selected!')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
            file.save(file_path)
            print(f"File saved to: {file_path}")

            wav_path = convert_to_wav(file_path)
            if wav_path:
                transcripts = transcribe_audio(wav_path)

                output_file = os.path.join(app.config['OUTPUT_FOLDER'], 'transcription.txt')
                try:
                    with open(output_file, 'w') as f:
                        for transcript in transcripts:
                            f.write(transcript + '\n')
                    print(f"Transcriptions saved to: {output_file}")
                except Exception as e:
                    print(f"Error saving transcriptions: {e}")
                    flash('Error saving transcriptions!')
                    return redirect(request.url)

                # Remover arquivos temporários
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    if os.path.exists(wav_path):
                        os.remove(wav_path)
                    print("Temporary files removed.")
                except Exception as e:
                    print(f"Error removing temporary files: {e}")

                return redirect(url_for('results', status='success'))

    return render_template('upload.html')

@app.route('/results')
def results():
    status = request.args.get('status', 'error')
    transcription_content = ""
    output_file = os.path.join(app.config['OUTPUT_FOLDER'], 'transcription.txt')

    if status == 'success':
        try:
            with open(output_file, 'r') as f:
                transcription_content = f.read()
        except FileNotFoundError:
            transcription_content = "No transcription available."

    return render_template('results.html', status=status, transcription_content=transcription_content)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)