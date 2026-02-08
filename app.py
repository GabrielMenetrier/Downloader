from flask import Flask, render_template, request, jsonify, send_file
import os
import yt_dlp
from pathlib import Path
import json
from datetime import datetime
import uuid
import subprocess

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

# Criar pasta de downloads se não existir
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Carregar modelo Whisper (usa o modelo base por padrão)
whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        import whisper
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
    """Processa um único vídeo: download e transcrição com sistema de ID puro"""
    video_id = str(uuid.uuid4())[:12]  # ID único de 12 caracteres
    
    # Detectar plataforma
    is_tiktok = 'tiktok.com' in url.lower()
    is_instagram = 'instagram.com' in url.lower()
    
    # Configurações base do yt-dlp com nome de arquivo simples baseado em ID
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': os.path.join(app.config['UPLOAD_FOLDER'], f'{video_id}_temp.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
        'extractor_retries': 3,
        'fragment_retries': 3,
        'skip_unavailable_fragments': True,
    }
    
    # Configurações específicas para TikTok
    if is_tiktok:
        ydl_opts.update({
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.tiktok.com/',
            },
            'extractor_args': {
                'tiktok': {
                    'api_hostname': 'api22-normal-c-useast2a.tiktokv.com'
                }
            }
        })
    
    # Configurações específicas para Instagram
    if is_instagram:
        ydl_opts.update({
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
        })
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extrair informações do vídeo
            info = ydl.extract_info(url, download=True)
            
            if not info:
                raise Exception("Não foi possível extrair informações do vídeo")
            
            video_title = info.get('title', 'Vídeo sem título')
            thumbnail = info.get('thumbnail', '')
            duration = info.get('duration', 0)
            
            # Criar nome curto do título (primeiras 5 letras/números)
            title_short = ''.join(c for c in video_title if c.isalnum())[:5].lower()
            if not title_short:
                title_short = 'video'
            
            # Encontrar o arquivo temporário baixado
            temp_video = ydl.prepare_filename(info)
            
            # Determinar extensão do arquivo
            video_ext = 'mp4'
            if os.path.exists(temp_video):
                video_ext = temp_video.split('.')[-1]
            else:
                # Procurar arquivo com ID
                downloads_dir = app.config['UPLOAD_FOLDER']
                matching_files = [f for f in os.listdir(downloads_dir) 
                                if f.startswith(f'{video_id}_temp')]
                if matching_files:
                    temp_video = os.path.join(downloads_dir, matching_files[0])
                    video_ext = matching_files[0].split('.')[-1]
                else:
                    raise Exception("Arquivo de vídeo não encontrado após download")
            
            # Renomear para formato padrão: id_short.ext
            final_video_name = f'{video_id}_{title_short}.{video_ext}'
            final_video_path = os.path.join(app.config['UPLOAD_FOLDER'], final_video_name)
            
            # Renomear arquivo
            if os.path.exists(temp_video):
                os.rename(temp_video, final_video_path)
            
            # Extrair áudio para transcrição
            audio_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(app.config['UPLOAD_FOLDER'], f'{video_id}_audio_temp.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': False,
            }
            
            # Adicionar headers se for TikTok ou Instagram
            if is_tiktok or is_instagram:
                audio_opts['http_headers'] = ydl_opts['http_headers']
            
            with yt_dlp.YoutubeDL(audio_opts) as ydl_audio:
                ydl_audio.download([url])
            
            # Encontrar e renomear arquivo de áudio
            audio_temp = os.path.join(app.config['UPLOAD_FOLDER'], f'{video_id}_audio_temp.mp3')
            audio_final = os.path.join(app.config['UPLOAD_FOLDER'], f'{video_id}_audio.mp3')
            
            # Se não encontrar .mp3, procurar outros formatos
            if not os.path.exists(audio_temp):
                downloads_dir = app.config['UPLOAD_FOLDER']
                audio_files = [f for f in os.listdir(downloads_dir) 
                             if f.startswith(f'{video_id}_audio_temp')]
                if audio_files:
                    audio_temp = os.path.join(downloads_dir, audio_files[0])
            
            # Renomear áudio
            if os.path.exists(audio_temp):
                os.rename(audio_temp, audio_final)
            
            # Transcrever áudio
            transcription = {
                'text': 'Transcrição não disponível',
                'language': 'unknown',
                'segments': []
            }
            
            if os.path.exists(audio_final):
                transcription = transcribe_audio(audio_final)
                # Limpar arquivo de áudio temporário
                os.remove(audio_final)
            
            return {
                'success': True,
                'video_id': video_id,
                'title': video_title,
                'title_short': title_short,
                'thumbnail': thumbnail,
                'duration': duration,
                'filename': final_video_name,  # Nome do arquivo final
                'transcription': transcription,
                'url': url
            }
    
    except Exception as e:
        error_message = str(e)
        # Mensagens de erro mais amigáveis
        if 'Unable to extract' in error_message or 'extract webpage' in error_message:
            error_message = "Este vídeo não pode ser baixado. Pode estar privado, restrito por região, ou a plataforma bloqueou o acesso."
        elif 'HTTP Error 404' in error_message:
            error_message = "Vídeo não encontrado. Verifique se o link está correto."
        elif 'Private video' in error_message:
            error_message = "Este vídeo é privado e não pode ser baixado."
        
        raise Exception(error_message)

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

@app.route('/download/<video_id>')
def download_file(video_id):
    """Rota para download de arquivos usando apenas o ID"""
    try:
        # Procurar arquivo que começa com o video_id
        downloads_dir = app.config['UPLOAD_FOLDER']
        
        # Encontrar arquivo com este ID
        matching_files = [f for f in os.listdir(downloads_dir) 
                         if f.startswith(video_id) and not f.endswith('_audio.mp3')]
        
        if not matching_files:
            return jsonify({'error': 'Arquivo não encontrado'}), 404
        
        filename = matching_files[0]
        file_path = os.path.join(downloads_dir, filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=filename)
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
    # Modo produção para Docker
    import os
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)