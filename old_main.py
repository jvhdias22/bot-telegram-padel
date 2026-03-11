import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- 1. CONFIGURAÇÃO DA BASE DE DADOS ---
def init_db():
    conn = sqlite3.connect('padel_gestao.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jogadores (
            telegram_id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            nivel TEXT
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS torneios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            nivel_exigido TEXT NOT NULL,
            vagas INTEGER NOT NULL
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inscricoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_jogador INTEGER NOT NULL,
            id_torneio INTEGER NOT NULL,
            UNIQUE(id_jogador, id_torneio)
        );
    ''')
    
    # Inserir torneios de exemplo se não existirem
    cursor.execute("SELECT count(*) FROM torneios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO torneios (nome, nivel_exigido, vagas) VALUES ('Torneio Abertura', 'L5', 4)")
        cursor.execute("INSERT INTO torneios (nome, nivel_exigido, vagas) VALUES ('Torneio Pro', 'L2', 4)")
        cursor.execute("INSERT INTO torneios (nome, nivel_exigido, vagas) VALUES ('Torneio Intermédio', 'L3', 4)")
    
    conn.commit()
    conn.close()

# --- 2. COMANDO START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Menu inicial com botões
    keyboard = [
        [InlineKeyboardButton("📝 Registar meu Nível", callback_data='menu_niveis')],
        [InlineKeyboardButton("🏆 Ver Torneios", callback_data='ver_torneios')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Olá {user.first_name}! Bem-vindo ao Gestor de Padel. 🎾\n"
        "Para começares, regista o teu nível de jogo:",
        reply_markup=reply_markup
    )

# --- 3. MENU DE NÍVEIS ---
async def menu_niveis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Nível 2 (Pro)", callback_data='set_L2'),
         InlineKeyboardButton("Nível 3", callback_data='set_L3')],
        [InlineKeyboardButton("Nível 4", callback_data='set_L4'),
         InlineKeyboardButton("Nível 5 (Iniciante)", callback_data='set_L5')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("Escolhe o teu nível de Padel:", reply_markup=reply_markup)

# --- 4. GUARDAR NO SQLITE ---
async def guardar_nivel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Extrair o nível do callback_data (ex: 'set_L3' -> 'L3')
    nivel_escolhido = query.data.split('_')[1]
    user_id = query.from_user.id
    nome = query.from_user.first_name

    conn = sqlite3.connect('padel_gestao.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO jogadores (telegram_id, nome, nivel) 
        VALUES (?, ?, ?)
    ''', (user_id, nome, nivel_escolhido))
    conn.commit()
    conn.close()

    await query.edit_message_text(f"✅ Boa! Estás registado como {nivel_escolhido}. Agora já te podes inscrever em torneios.")

# --- 5. VER TORNEIOS ---
async def ver_torneios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    conn = sqlite3.connect('padel_gestao.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, nivel_exigido, vagas FROM torneios")
    torneios = cursor.fetchall()
    conn.close()

    if not torneios:
        await query.edit_message_text("Não há torneios disponíveis de momento.")
        return

    # Criar botões para cada torneio
    keyboard = []
    for t in torneios:
        t_id, t_nome, t_nivel, t_vagas = t
        texto = f"{t_nome} ({t_nivel}) - {t_vagas} vagas"
        keyboard.append([InlineKeyboardButton(f"Inscrever: {t_nome}", callback_data=f'inscrever_{t_id}')])
        keyboard.append([InlineKeyboardButton(f"📜 Ver Inscritos: {t_nome}", callback_data=f'lista_{t_id}')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🏆 Torneios Disponíveis:", reply_markup=reply_markup)

# --- 6. REALIZAR INSCRIÇÃO ---
async def realizar_inscricao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    torneio_id = query.data.split('_')[1]

    conn = sqlite3.connect('padel_gestao.db')
    cursor = conn.cursor()

    # 1. Busca o nível do jogador
    cursor.execute("SELECT nivel FROM jogadores WHERE telegram_id = ?", (user_id,))
    jogador = cursor.fetchone()
    
    # 2. Busca as regras do torneio
    cursor.execute("SELECT nome, nivel_exigido, vagas FROM torneios WHERE id = ?", (torneio_id,))
    torneio = cursor.fetchone()

    if not jogador:
        await query.answer("Primeiro, regista o teu nível no menu principal! ⚠️", show_alert=True)
    elif jogador[0] != torneio[1]:
        await query.answer(f"Nível incompatível! Este torneio é para {torneio[1]} e tu és {jogador[0]}. ❌", show_alert=True)
    else:
        # 3. Verifica se ainda há vagas (Vê quantos já estão inscritos)
        cursor.execute("SELECT COUNT(*) FROM inscricoes WHERE id_torneio = ?", (torneio_id,))
        total_inscritos = cursor.fetchone()[0]
        
        if total_inscritos >= torneio[2]:
            await query.answer("Torneio cheio! 🚫", show_alert=True)
        else:
            try:
                cursor.execute("INSERT INTO inscricoes (id_jogador, id_torneio) VALUES (?, ?)", (user_id, torneio_id))
                conn.commit()
                await query.edit_message_text(f"✅ Confirmado! Estás inscrito no {torneio[0]}. Prepara a raquete!")
            except sqlite3.IntegrityError:
                await query.answer("Já estás na lista deste torneio! 😎", show_alert=True)
    
    conn.close()

# --- 7. LISTAR JOGADORES ---
async def listar_jogadores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    torneio_id = query.data.split('_')[1]

    conn = sqlite3.connect('padel_gestao.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT j.nome FROM jogadores j
        JOIN inscricoes i ON j.telegram_id = i.id_jogador
        WHERE i.id_torneio = ?
    ''', (torneio_id,))
    inscritos = cursor.fetchall()
    conn.close()

    texto = "<b>👥 Inscritos:</b>\n"
    if not inscritos:
        texto += "Ainda não há inscritos. Sê o primeiro!"
    else:
        for i, (nome,) in enumerate(inscritos, 1):
            texto += f"{i}. {nome}\n"
    
    await query.edit_message_text(texto, parse_mode='HTML')

# --- 5. EXECUÇÃO DO BOT ---
if __name__ == '__main__':
    init_db() # Cria o ficheiro .db se não existir
    
    # Coloca aqui o Token que o @BotFather te deu
    TOKEN = '8580100917:AAGOmvbDsfFWrJqJPqKgomzcRB7Tgrenrbs' 
    
    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_niveis, pattern='^menu_niveis$'))
    app.add_handler(CallbackQueryHandler(guardar_nivel, pattern='^set_'))
    app.add_handler(CallbackQueryHandler(ver_torneios, pattern='^ver_torneios$'))
    app.add_handler(CallbackQueryHandler(realizar_inscricao, pattern='^inscrever_'))
    app.add_handler(CallbackQueryHandler(listar_jogadores, pattern='^lista_'))

    print("Bot de Padel Online! Prime CTRL+C para parar.")
    app.run_polling()
