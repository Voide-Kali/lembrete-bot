# Central de Lembretes

Bot Telegram para criar lembretes em linguagem natural, consultar a agenda,
cancelar eventos e adiar notificações por botões.

## Instalação

```bash
git clone https://github.com/Voide-Kali/lembrete-bot.git
cd lembrete-bot
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
cp config.example.py config.py
```

Configure no `.env`:

- `LEMBRETE_TELEGRAM_TOKEN`;
- `ALLOWED_CHAT_ID`;
- `TIMEZONE`;
- `GROQ_API_KEY`;
- `GROQ_MODEL`.

## Comandos

- `/painel`
- `/lembretes`
- `/cancelar`
- `/ajuda`
