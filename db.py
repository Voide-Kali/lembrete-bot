import sqlite3
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
DB_FILE = Path(__file__).resolve().parent / "lembretes.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lembretes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            username TEXT,
            mensagem TEXT NOT NULL,
            quando TIMESTAMP NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            enviado INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Banco de dados inicializado.")


def salvar_lembrete(chat_id: str, username: str, mensagem: str, quando: str) -> int:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO lembretes (chat_id, username, mensagem, quando) VALUES (?, ?, ?, ?)",
        (chat_id, username, mensagem, quando)
    )
    lembrete_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return lembrete_id


def listar_lembretes(chat_id: str) -> list:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, mensagem, quando FROM lembretes WHERE chat_id = ? AND enviado = 0 ORDER BY quando ASC",
        (chat_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def cancelar_lembrete(lembrete_id: int, chat_id: str) -> bool:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM lembretes WHERE id = ? AND chat_id = ?",
        (lembrete_id, chat_id)
    )
    deletado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deletado


def buscar_pendentes(agora: datetime) -> list:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, chat_id, mensagem FROM lembretes "
        "WHERE enviado = 0 AND quando <= ? ORDER BY quando ASC",
        (agora.strftime("%Y-%m-%d %H:%M:%S"),),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def marcar_enviado(lembrete_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE lembretes SET enviado = 1 WHERE id = ?", (lembrete_id,))
    conn.commit()
    conn.close()


def adiar_lembrete(lembrete_id: int, chat_id: str, quando: datetime) -> bool:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE lembretes SET quando = ?, enviado = 0 WHERE id = ? AND chat_id = ?",
        (quando.strftime("%Y-%m-%d %H:%M:%S"), lembrete_id, chat_id),
    )
    atualizado = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return atualizado


def contar_enviados(chat_id: str) -> int:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM lembretes WHERE chat_id = ? AND enviado = 1",
        (chat_id,),
    )
    total = cursor.fetchone()[0]
    conn.close()
    return total
