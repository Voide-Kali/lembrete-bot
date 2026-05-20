import requests
import logging
import json
from datetime import datetime
import pytz
from config import GROQ_API_KEY, GROQ_MODEL, TIMEZONE

logger = logging.getLogger(__name__)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def interpretar_lembrete(texto: str) -> dict | None:
    """
    Usa o Groq para extrair a mensagem e o horario do texto em linguagem natural.
    Retorna {"mensagem": "...", "quando": "YYYY-MM-DD HH:MM:SS"} ou None se falhar.
    """
    agora = datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")

    prompt = f"""Voce e um assistente que extrai informacoes de lembretes em portugues.

Data e hora atual: {agora} (fuso horario: {TIMEZONE})

O usuario enviou: "{texto}"

Extraia:
1. O que ele quer ser lembrado (a mensagem do lembrete)
2. Quando ele quer ser lembrado (data e hora exata)

Responda APENAS com um JSON valido, sem texto extra, sem markdown, no formato:
{{"mensagem": "texto do lembrete", "quando": "YYYY-MM-DD HH:MM:SS"}}

Regras:
- Se o usuario disser "as 19h", use 19:00:00 da data de hoje (ou amanha se ja passou)
- Se disser "amanha as 8h", use amanha 08:00:00
- Se disser "daqui 30 minutos", some 30 minutos ao horario atual
- Se nao conseguir interpretar, responda: {{"erro": "nao entendi"}}"""

    try:
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.1,
            },
            timeout=15
        )

        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"].strip()
            content = content.replace("```json", "").replace("```", "").strip()
            data = json.loads(content)

            if "erro" in data:
                return None

            return data
        else:
            logger.error(f"Groq erro {response.status_code}: {response.text}")
            return None

    except Exception as e:
        logger.error(f"Erro ao interpretar lembrete: {e}")
        return None
