import sqlite3
import os

DB_NAME = os.getenv('DB_PATH', 'padel_gestao.db')

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jogadores (
                telegram_id INTEGER PRIMARY KEY,
                nome TEXT NOT NULL,
                phone_number TEXT UNIQUE
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS torneios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                vagas INTEGER NOT NULL,
                data_hora TEXT
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inscricoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_jogador INTEGER NOT NULL,
                id_torneio INTEGER NOT NULL,
                posicao TEXT,
                UNIQUE(id_jogador, id_torneio)
            );
        ''')
        # Migração: adicionar coluna data_hora se não existir (BD já criada)
        try:
            cursor.execute("ALTER TABLE torneios ADD COLUMN data_hora TEXT")
        except Exception:
            pass
        # Migração: adicionar coluna suplente se não existir
        try:
            cursor.execute("ALTER TABLE inscricoes ADD COLUMN suplente INTEGER DEFAULT 0")
        except Exception:
            pass

def get_jogador(telegram_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id, nome, phone_number FROM jogadores WHERE telegram_id = ?", (telegram_id,))
        return cursor.fetchone()

def get_jogador_by_phone(phone_number):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id, nome, phone_number FROM jogadores WHERE phone_number = ?", (phone_number,))
        return cursor.fetchone()

def is_inscrito(user_id, torneio_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM inscricoes WHERE id_jogador = ? AND id_torneio = ?", (user_id, torneio_id))
        return cursor.fetchone() is not None

def count_suplentes(torneio_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM inscricoes WHERE id_torneio = ? AND suplente = 1", (torneio_id,))
        return cursor.fetchone()[0]

def save_jogador(telegram_id, nome, phone_number=None):
    with get_connection() as conn:
        conn.execute(
            'INSERT OR REPLACE INTO jogadores (telegram_id, nome, phone_number) VALUES (?, ?, ?)',
            (telegram_id, nome, phone_number)
        )

def get_torneios():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, vagas, data_hora FROM torneios")
        return cursor.fetchall()

def get_torneio(torneio_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT nome, vagas, data_hora FROM torneios WHERE id = ?", (torneio_id,))
        return cursor.fetchone()

def count_inscritos(torneio_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM inscricoes WHERE id_torneio = ?", (torneio_id,))
        return cursor.fetchone()[0]

def inscrever_jogador(user_id, torneio_id, posicao, suplente=False):
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO inscricoes (id_jogador, id_torneio, posicao, suplente) VALUES (?, ?, ?, ?)",
                (user_id, torneio_id, posicao, 1 if suplente else 0)
            )
        return True
    except sqlite3.IntegrityError:
        return False

def get_inscritos_nomes(torneio_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT j.nome, i.posicao, i.suplente FROM jogadores j
            JOIN inscricoes i ON j.telegram_id = i.id_jogador
            WHERE i.id_torneio = ?
            ORDER BY i.suplente ASC, i.id ASC
        ''', (torneio_id,))
        return cursor.fetchall()

def remove_inscricao(user_id, torneio_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inscricoes WHERE id_jogador = ? AND id_torneio = ?", (user_id, torneio_id))
        return cursor.rowcount > 0

def criar_torneio(nome, vagas, data_hora=None):
    with get_connection() as conn:
        conn.execute("INSERT INTO torneios (nome, vagas, data_hora) VALUES (?, ?, ?)", (nome, vagas, data_hora))

def apagar_torneio(torneio_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM inscricoes WHERE id_torneio = ?", (torneio_id,))
        conn.execute("DELETE FROM torneios WHERE id = ?", (torneio_id,))
