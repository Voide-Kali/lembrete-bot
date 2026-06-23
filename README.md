# Central de Lembretes

Bot do Telegram para criar lembretes em linguagem natural, consultar a agenda, cancelar eventos e adiar notificações por botões.

## Componentes

- `main.py`: fluxo principal do bot
- `parser.py`: leitura de linguagem natural
- `db.py`: persistência dos lembretes
- `config.py` e `config.example.py`: configuração local
- `lembrete-bot.service`: execução como serviço

## Instalação

```bash
git clone https://github.com/Voide-Kali/lembrete-bot.git
cd lembrete-bot
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
cp config.example.py config.py
```

## Configuração

- preencha `LEMBRETE_TELEGRAM_TOKEN`;
- defina `ALLOWED_CHAT_ID`;
- ajuste `TIMEZONE`;
- configure `GROQ_API_KEY` e `GROQ_MODEL` se quiser geração com IA.

## Execução

```bash
. venv/bin/activate
python3 main.py
```

## Estrutura

```text
lembrete-bot/
├── main.py
├── parser.py
├── db.py
├── config.py
├── config.example.py
├── lembrete-bot.service
└── README.md
```

## Governança

- [LICENSE](LICENSE)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CHANGELOG.md](CHANGELOG.md)
