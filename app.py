from flask import Flask, render_template, request, jsonify, send_file
import os
import yt_dlp
import whisper
from pathlib import Path
import tempfile
import json
from datetime import datetime
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

# Criar pasta de downloads se não existir
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Carregar modelo Whisper (usa o modelo base por padrão)
# Para melhor precisão, pode usar 'medium' ou 'large'
whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        whisper_model = whisper.load_model("base")
    return whisper_model

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_videos', methods=['POST'])
def process_videos():
    try:
        data = request.get_json()
        urls = data.get('urls', [])
        
        if not urls:
            return jsonify({'error': 'Nenhum URL fornecido'}), 400
        
        results = []
        
        for url in urls:
            try:
                result = process_single_video(url)
                results.append(result)
            except Exception as e:
                results.append({
                    'url': url,
                    'error': str(e),
                    'success': False
                })
        
        return jsonify({'results': results})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_single_video(url):
    """Processa um único vídeo: download e transcrição"""
    video_id = str(uuid.uuid4())[:8]
    
    # Configurações do yt-dlp
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': os.path.join(app.config['UPLOAD_FOLDER'], f'{video_id}_%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Extrair informações do vídeo
        info = ydl.extract_info(url, download=True)
        
        video_title = info.get('title', 'Vídeo sem título')
        thumbnail = info.get('thumbnail', '')
        duration = info.get('duration', 0)
        
        # Encontrar o arquivo baixado
        video_filename = ydl.prepare_filename(info)
        
        # Extrair áudio para transcrição
        audio_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(app.config['UPLOAD_FOLDER'], f'{video_id}_audio.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(audio_opts) as ydl_audio:
            ydl_audio.download([url])
        
        # Encontrar arquivo de áudio
        audio_file = os.path.join(app.config['UPLOAD_FOLDER'], f'{video_id}_audio.mp3')
        
        # Transcrever áudio
        transcription = transcribe_audio(audio_file)
        
        # Limpar arquivo de áudio temporário
        if os.path.exists(audio_file):
            os.remove(audio_file)
        
        return {
            'success': True,
            'video_id': video_id,
            'title': video_title,
            'thumbnail': thumbnail,
            'duration': duration,
            'download_path': os.path.basename(video_filename),
            'transcription': transcription,
            'url': url
        }

def transcribe_audio(audio_path):
    """Transcreve áudio usando Whisper"""
    try:
        model = get_whisper_model()
        result = model.transcribe(audio_path, language=None)  # Auto-detecta idioma
        
        return {
            'text': result['text'],
            'language': result.get('language', 'desconhecido'),
            'segments': [
                {
                    'start': seg['start'],
                    'end': seg['end'],
                    'text': seg['text']
                }
                for seg in result.get('segments', [])
            ]
        }
    except Exception as e:
        return {
            'text': f'Erro na transcrição: {str(e)}',
            'language': 'error',
            'segments': []
        }

@app.route('/download/<filename>')
def download_file(filename):
    """Rota para download de arquivos"""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'Arquivo não encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Remove arquivos antigos da pasta de downloads"""
    try:
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        return jsonify({'success': True, 'message': 'Arquivos removidos com sucesso'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
