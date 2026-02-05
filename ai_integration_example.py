"""
EXEMPLO: Integração futura com IA para geração de roteiros
Este arquivo demonstra como você pode adicionar funcionalidades de IA ao app

Para usar:
1. Instale: pip install openai anthropic
2. Configure suas chaves de API
3. Adicione as rotas ao app.py
4. Integre ao frontend
"""

import os
from typing import List, Dict

# Exemplo com OpenAI GPT
def generate_script_with_openai(transcriptions: List[Dict]) -> str:
    """
    Gera um novo roteiro baseado nas transcrições usando OpenAI GPT
    
    Args:
        transcriptions: Lista de dicionários com transcrições
        
    Returns:
        Roteiro gerado
    """
    try:
        import openai
        
        # Configure sua chave API
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        
        # Combinar transcrições
        combined_text = "\n\n---\n\n".join([
            f"Vídeo {i+1} ({t.get('language', 'unknown')}):\n{t['text']}"
            for i, t in enumerate(transcriptions)
        ])
        
        # Criar prompt
        prompt = f"""
        Analise as seguintes transcrições de vídeos e crie um novo roteiro criativo
        que combine os melhores elementos de cada um:
        
        {combined_text}
        
        Crie um roteiro estruturado com:
        - Gancho inicial (10s)
        - Desenvolvimento (corpo principal)
        - Conclusão/CTA
        
        Mantenha o estilo e tom similares aos vídeos originais.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um criador de roteiros para vídeos curtos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Erro ao gerar roteiro: {str(e)}"


# Exemplo com Anthropic Claude
def generate_script_with_claude(transcriptions: List[Dict]) -> str:
    """
    Gera um novo roteiro baseado nas transcrições usando Anthropic Claude
    
    Args:
        transcriptions: Lista de dicionários com transcrições
        
    Returns:
        Roteiro gerado
    """
    try:
        import anthropic
        
        # Configure sua chave API
        client = anthropic.Anthropic(
            api_key=os.environ.get('ANTHROPIC_API_KEY')
        )
        
        # Combinar transcrições
        combined_text = "\n\n---\n\n".join([
            f"Vídeo {i+1} ({t.get('language', 'unknown')}):\n{t['text']}"
            for i, t in enumerate(transcriptions)
        ])
        
        # Criar prompt
        prompt = f"""
        Analise as seguintes transcrições de vídeos e crie um novo roteiro criativo:
        
        {combined_text}
        
        Crie um roteiro para vídeo curto (até 60 segundos) com estrutura clara.
        """
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return message.content[0].text
        
    except Exception as e:
        return f"Erro ao gerar roteiro: {str(e)}"


# Exemplo de análise de conteúdo
def analyze_video_content(transcription: Dict) -> Dict:
    """
    Analisa o conteúdo de uma transcrição
    
    Returns:
        Dicionário com análises
    """
    text = transcription.get('text', '')
    
    # Análises básicas
    analysis = {
        'word_count': len(text.split()),
        'char_count': len(text),
        'language': transcription.get('language', 'unknown'),
        'duration': transcription.get('duration', 0),
        'sentiment': 'neutral',  # Placeholder
        'topics': [],  # Placeholder
        'keywords': []  # Placeholder
    }
    
    # Aqui você pode adicionar:
    # - Análise de sentimento (TextBlob, VADER, etc.)
    # - Extração de tópicos (LDA, NMF)
    # - Extração de palavras-chave (TF-IDF, RAKE)
    # - Detecção de entidades (spaCy, NLTK)
    
    return analysis


# Exemplo de resumo automático
def generate_summary(transcription: Dict, max_sentences: int = 3) -> str:
    """
    Gera um resumo da transcrição
    
    Args:
        transcription: Dicionário com transcrição
        max_sentences: Número máximo de sentenças no resumo
        
    Returns:
        Resumo do texto
    """
    try:
        from transformers import pipeline
        
        # Usar modelo de sumarização
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        
        text = transcription.get('text', '')
        
        # Limitar tamanho do input
        max_input_length = 1024
        if len(text.split()) > max_input_length:
            text = ' '.join(text.split()[:max_input_length])
        
        summary = summarizer(
            text,
            max_length=130,
            min_length=30,
            do_sample=False
        )
        
        return summary[0]['summary_text']
        
    except Exception as e:
        # Fallback: pegar primeiras sentenças
        sentences = transcription.get('text', '').split('.')
        return '. '.join(sentences[:max_sentences]) + '.'


# Exemplo de detecção de momentos-chave
def detect_key_moments(transcription: Dict) -> List[Dict]:
    """
    Detecta momentos-chave no vídeo baseado na transcrição
    
    Returns:
        Lista de momentos com timestamp e descrição
    """
    segments = transcription.get('segments', [])
    key_moments = []
    
    # Palavras que indicam momentos importantes
    keywords = [
        'importante', 'lembre-se', 'crucial', 'essencial', 
        'primeiro', 'segundo', 'terceiro', 'finalmente',
        'atenção', 'cuidado', 'dica', 'segredo'
    ]
    
    for segment in segments:
        text = segment.get('text', '').lower()
        
        # Verificar se contém palavras-chave
        if any(keyword in text for keyword in keywords):
            key_moments.append({
                'timestamp': segment.get('start', 0),
                'text': segment.get('text', ''),
                'importance': 'high'
            })
    
    return key_moments


# Exemplo de geração de hashtags
def generate_hashtags(transcription: Dict, max_tags: int = 10) -> List[str]:
    """
    Gera hashtags relevantes baseadas na transcrição
    
    Returns:
        Lista de hashtags
    """
    # Implementação básica
    # Você pode melhorar com NLP mais avançado
    
    text = transcription.get('text', '').lower()
    words = text.split()
    
    # Palavras comuns para remover
    stopwords = {'o', 'a', 'de', 'da', 'do', 'em', 'um', 'uma', 'os', 'as'}
    
    # Contar frequência
    from collections import Counter
    word_freq = Counter(
        word for word in words 
        if len(word) > 3 and word not in stopwords
    )
    
    # Pegar as mais frequentes
    top_words = [word for word, _ in word_freq.most_common(max_tags)]
    
    # Converter para hashtags
    hashtags = [f"#{word}" for word in top_words]
    
    return hashtags


# Rotas Flask para adicionar ao app.py
"""
@app.route('/ai/generate_script', methods=['POST'])
def ai_generate_script():
    data = request.get_json()
    transcriptions = data.get('transcriptions', [])
    
    # Escolher provedor de IA
    provider = data.get('provider', 'openai')
    
    if provider == 'openai':
        script = generate_script_with_openai(transcriptions)
    elif provider == 'claude':
        script = generate_script_with_claude(transcriptions)
    else:
        return jsonify({'error': 'Provedor inválido'}), 400
    
    return jsonify({'script': script})

@app.route('/ai/analyze', methods=['POST'])
def ai_analyze():
    data = request.get_json()
    transcription = data.get('transcription', {})
    
    analysis = analyze_video_content(transcription)
    summary = generate_summary(transcription)
    key_moments = detect_key_moments(transcription)
    hashtags = generate_hashtags(transcription)
    
    return jsonify({
        'analysis': analysis,
        'summary': summary,
        'key_moments': key_moments,
        'hashtags': hashtags
    })
"""
