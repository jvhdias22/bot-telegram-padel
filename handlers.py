import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import BadRequest
import database as db

logger = logging.getLogger(__name__)

# Constante para o ConversationHandler
AGUARDAR_NUMERO = 1

# ADMIN_ID carregado uma vez no arranque
ADMIN_ID = os.getenv('ADMIN_ID')

# --- MENUS AUXILIARES ---
def get_main_menu_keyboard(user_id=None):
    keyboard = [
        [InlineKeyboardButton("🏆 Ver Torneios", callback_data='ver_torneios')],
        [InlineKeyboardButton("ℹ️ Ajuda", callback_data='ajuda')]
    ]
    if ADMIN_ID and str(user_id) == str(ADMIN_ID):
        keyboard.append([InlineKeyboardButton("⚙️ Painel Admin", callback_data='admin_panel')])
    return keyboard

def get_back_button(callback_data='menu_principal'):
    return [InlineKeyboardButton("🔙 Voltar", callback_data=callback_data)]

# --- HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Se for callback (botão "Voltar"), editamos a mensagem. Se for comando /start, enviamos nova.
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except BadRequest:
            pass
        try:
            await update.callback_query.edit_message_text(
                f"Olá {user.first_name}! Bem-vindo ao Gestor de Padel. 🎾\nO que queres fazer?",
                reply_markup=InlineKeyboardMarkup(get_main_menu_keyboard(user.id))
            )
        except BadRequest as e:
            if "Message is not modified" in str(e):
                pass
            else:
                raise e
    else:
        await update.message.reply_text(
            f"Olá {user.first_name}! Bem-vindo ao Gestor de Padel. 🎾\nO que queres fazer?",
            reply_markup=InlineKeyboardMarkup(get_main_menu_keyboard(user.id))
        )

async def ver_torneios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except BadRequest:
        pass

    torneios = db.get_torneios()

    if not torneios:
        keyboard = [get_back_button()]
        await query.edit_message_text("Não há torneios disponíveis de momento.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    keyboard = []
    for t in torneios:
        t_id, t_nome, t_vagas, t_data_hora = t
        inscritos = db.count_inscritos(t_id)
        data_str = f" 📅{t_data_hora}" if t_data_hora else ""
        texto_botao = f"{t_nome}{data_str} [{inscritos}/{t_vagas}]"
        keyboard.append([InlineKeyboardButton(texto_botao, callback_data=f'detalhe_{t_id}')])
    
    keyboard.append(get_back_button())
    try:
        await query.edit_message_text("🏆 <b>Torneios Disponíveis:</b>\nClica para ver detalhes e inscrever.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e
            
def get_tournament_details(torneio_id):
    torneio = db.get_torneio(torneio_id)
    if not torneio:
        return "Torneio não encontrado.", InlineKeyboardMarkup([get_back_button('ver_torneios')])

    nome, vagas, data_hora = torneio
    todos_inscritos = db.get_inscritos_nomes(torneio_id)
    titulares = [(n, p) for n, p, s in todos_inscritos if not s]
    suplentes = [(n, p) for n, p, s in todos_inscritos if s]
    total_titulares = len(titulares)
    total_suplentes = len(suplentes)

    texto = f"🎾 <b>{nome}</b>\n"
    if data_hora:
        texto += f"📅 <b>Data:</b> {data_hora}\n"
    texto += f"Vagas: {total_titulares}/{vagas}\n\n"
    texto += "<b>Inscritos:</b>\n"

    if not titulares:
        texto += "Ninguém ainda.\n"
    else:
        for i, (nome_inscrito, posicao) in enumerate(titulares, 1):
            posicao_str = f"({posicao})" if posicao else ""
            texto += f"{i}. {nome_inscrito} {posicao_str}\n"

    if suplentes:
        texto += "\n<b>🔄 Suplentes:</b>\n"
        for i, (nome_inscrito, posicao) in enumerate(suplentes, 1):
            posicao_str = f"({posicao})" if posicao else ""
            texto += f"{i}. {nome_inscrito} {posicao_str}\n"

    keyboard_buttons = []
    if total_titulares < vagas:
        keyboard_buttons.append([InlineKeyboardButton("✅ Inscrever", callback_data=f'inscrever_{torneio_id}')])
    elif total_suplentes < 2:
        texto += "\n🚫 <b>Torneio Cheio!</b>"
        keyboard_buttons.append([InlineKeyboardButton("📋 Entrar como Suplente", callback_data=f'inscrever_suplente_{torneio_id}')])
    else:
        texto += "\n🚫 <b>Torneio Cheio!</b> (Suplentes esgotados)"

    keyboard_buttons.append([InlineKeyboardButton("❌ Sair do Torneio", callback_data=f'sair_{torneio_id}')])
    keyboard_buttons.append(get_back_button('ver_torneios'))

    return texto, InlineKeyboardMarkup(keyboard_buttons)

async def detalhe_torneio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    torneio_id = int(query.data.split('_')[1])
    texto, keyboard = get_tournament_details(torneio_id)
    
    await query.edit_message_text(texto, reply_markup=keyboard, parse_mode='HTML')

async def realizar_inscricao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    torneio_id = int(query.data.split('_')[1])

    keyboard = [
        [InlineKeyboardButton("Individualmente", callback_data=f'inscricao_individual_{torneio_id}')],
        [InlineKeyboardButton("Com Parceiro", callback_data=f'inscricao_parceiro_{torneio_id}')],
        get_back_button(f'detalhe_{torneio_id}')
    ]

    await query.edit_message_text(
        "Como te queres inscrever?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def inscrever_suplente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    torneio_id = int(query.data.split('_')[2])
    user_id = query.from_user.id

    if db.is_inscrito(user_id, torneio_id):
        await query.answer("Já estás inscrito neste torneio!", show_alert=True)
        return

    if db.count_suplentes(torneio_id) >= 2:
        await query.answer("Já não há vagas de suplente!", show_alert=True)
        return

    keyboard = [
        [
            InlineKeyboardButton("Esquerda", callback_data=f'inscricao_posicao_{torneio_id}_E_suplente'),
            InlineKeyboardButton("Direita", callback_data=f'inscricao_posicao_{torneio_id}_D_suplente')
        ],
        get_back_button(f'detalhe_{torneio_id}')
    ]
    await query.edit_message_text(
        "Em que lado queres jogar como suplente?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def inscricao_individual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    torneio_id = int(query.data.split('_')[2])

    torneio = db.get_torneio(torneio_id)

    vagas = torneio[1]
    inscritos = db.count_inscritos(torneio_id)
    
    if inscritos >= vagas:
        await query.answer("O torneio está cheio!", show_alert=True)
        return

    # Verificar se já está inscrito pelo user_id
    if db.is_inscrito(user_id, torneio_id):
        await query.answer("Já estás inscrito!", show_alert=True)
        return

    keyboard = [
        [
            InlineKeyboardButton("Esquerda", callback_data=f'inscricao_posicao_{torneio_id}_E_individual'),
            InlineKeyboardButton("Direita", callback_data=f'inscricao_posicao_{torneio_id}_D_individual')
        ],
        get_back_button(f'detalhe_{torneio_id}')
    ]
    await query.edit_message_text(
        "Em que lado queres jogar?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def realizar_inscricao_posicao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    parts = query.data.split('_')
    torneio_id = int(parts[2])
    posicao_code = parts[3]
    tipo = parts[4] if len(parts) > 4 else 'individual'
    posicao = "Esquerda" if posicao_code == 'E' else "Direita"
    is_suplente = (tipo == 'suplente')

    # Garantir que o jogador existe na tabela antes de inscrever
    db.save_jogador(user_id, query.from_user.full_name)

    sucesso = db.inscrever_jogador(user_id, torneio_id, posicao, suplente=is_suplente)

    if sucesso:
        label = "Suplente" if is_suplente else f"'{posicao}'"
        await query.answer(f"Inscrição como {label} realizada!")
        texto, keyboard = get_tournament_details(torneio_id)
        await query.edit_message_text(texto, reply_markup=keyboard, parse_mode='HTML')
        await send_tournament_update_to_group(context, torneio_id)
    else:
        await query.answer("Ocorreu um erro. Talvez já estejas inscrito.", show_alert=True)

async def send_tournament_update_to_group(context: ContextTypes.DEFAULT_TYPE, torneio_id: int):
    group_id = os.getenv('GROUP_ID')
    if not group_id:
        logger.warning("GROUP_ID não definido no .env. Não é possível enviar atualizações para o grupo.")
        return

    torneio = db.get_torneio(torneio_id)
    if not torneio:
        return

    nome, vagas = torneio
    todos_inscritos = db.get_inscritos_nomes(torneio_id)
    titulares = [(n, p) for n, p, s in todos_inscritos if not s]
    suplentes = [(n, p) for n, p, s in todos_inscritos if s]

    texto_grupo = f"🎾 <b>Atualização de Torneio: {nome}</b>\n"
    texto_grupo += f"Vagas: {len(titulares)}/{vagas}\n\n"
    texto_grupo += "<b>Inscritos:</b>\n"
    if not titulares:
        texto_grupo += "Ninguém ainda.\n"
    else:
        for i, (player_name, posicao) in enumerate(titulares, 1):
            posicao_str = f" ({posicao})" if posicao else ""
            texto_grupo += f"{i}. {player_name}{posicao_str}\n"

    if suplentes:
        texto_grupo += "\n<b>🔄 Suplentes:</b>\n"
        for i, (player_name, posicao) in enumerate(suplentes, 1):
            posicao_str = f" ({posicao})" if posicao else ""
            texto_grupo += f"{i}. {player_name}{posicao_str}\n"
    
    try:
        await context.bot.send_message(chat_id=group_id, text=texto_grupo, parse_mode='HTML')
    except BadRequest as e:
        logger.error(f"Erro ao enviar mensagem para o grupo: {e}")

async def sair_torneio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    torneio_id = int(query.data.split('_')[1])
    
    removido = db.remove_inscricao(user_id, torneio_id)
    
    if removido:
        await query.answer("Inscrição cancelada.")
        texto, keyboard = get_tournament_details(torneio_id)
        await query.edit_message_text(texto, reply_markup=keyboard, parse_mode='HTML')
        await send_tournament_update_to_group(context, torneio_id)
    else:
        await query.answer("Não estavas inscrito neste torneio.", show_alert=True)

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    texto = (
        "<b>ℹ️ Ajuda</b>\n\n"
        "1. Vai a 'Meu Perfil' para definir o teu nível.\n"
        "2. Consulta 'Ver Torneios' para veres jogos disponíveis.\n"
        "3. Inscreve-te apenas em torneios do teu nível.\n"
        "4. Diverte-te!\n\n"
        "Dúvidas? Contacta o admin."
    )
    keyboard = [get_back_button()]
    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not ADMIN_ID or str(query.from_user.id) != str(ADMIN_ID):
        await query.answer("Não tens permissão.", show_alert=True)
        return

    texto = (
        "<b>⚙️ Painel de Administrador</b>\n\n"
        "Comandos disponíveis (escreve no chat):\n"
        "• <code>/criartorneio &lt;Nome&gt; &lt;DD/MM/AAAA&gt; &lt;HH:MM&gt; &lt;Vagas&gt;</code>\n"
        "  Ex: <i>/criartorneio SábadoManhã 15/03/2026 10:00 8</i>\n\n"
        "• <code>/criartorneio &lt;Nome&gt; &lt;Vagas&gt;</code> (sem data)\n"
        "  Ex: <i>/criartorneio SábadoManhã 8</i>\n\n"
        "• <code>/apagartorneio &lt;ID&gt;</code>\n"
        "  Ex: <i>/apagartorneio 2</i>"
    )
    keyboard = [get_back_button()]
    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def comando_criar_torneio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not ADMIN_ID or str(user_id) != str(ADMIN_ID):
        return

    try:
        args = context.args
        # Formatos aceites:
        # /criartorneio <Nome> <DD/MM/AAAA> <HH:MM> <Vagas>
        # /criartorneio <Nome> <Vagas>
        if len(args) < 2:
            await update.message.reply_text(
                "❌ Uso incorreto.\n"
                "Com data: /criartorneio <Nome> <DD/MM/AAAA> <HH:MM> <Vagas>\n"
                "Sem data: /criartorneio <Nome> <Vagas>"
            )
            return

        # Detectar se o penúltimo arg é hora (HH:MM) e o antepenúltimo é data (DD/MM/AAAA)
        import re
        data_hora = None
        if len(args) >= 4 and re.match(r'^\d{2}/\d{2}/\d{4}$', args[-3]) and re.match(r'^\d{2}:\d{2}$', args[-2]):
            vagas = int(args[-1])
            data_hora = f"{args[-3]} {args[-2]}"
            nome = " ".join(args[:-3])
        else:
            vagas = int(args[-1])
            nome = " ".join(args[:-1])

        db.criar_torneio(nome, vagas, data_hora)
        data_str = f" em {data_hora}" if data_hora else ""
        await update.message.reply_text(f"✅ Torneio '{nome}'{data_str} ({vagas} vagas) criado com sucesso!")
    except ValueError:
        await update.message.reply_text("❌ Vagas deve ser um número inteiro.")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")

async def comando_apagar_torneio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not ADMIN_ID or str(user_id) != str(ADMIN_ID):
        return

    try:
        tid = int(context.args[0])
        db.apagar_torneio(tid)
        await update.message.reply_text(f"✅ Torneio {tid} apagado.")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Uso: /apagartorneio <ID>")

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"O teu ID é: `{user_id}`\nO ID deste chat é: `{chat_id}`", parse_mode='Markdown')

async def inscricao_parceiro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    torneio_id = int(query.data.split('_')[2])
    context.user_data['torneio_id'] = torneio_id
    await query.edit_message_text("Por favor, envia o número de telemóvel do teu parceiro.")
    return AGUARDAR_NUMERO

async def aguardar_numero(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone_number = update.message.text.strip()
    torneio_id = context.user_data.get('torneio_id')

    if not torneio_id:
        await update.message.reply_text("Ocorreu um erro. Tenta novamente.")
        return ConversationHandler.END

    user = update.effective_user
    user_id = user.id

    # Guardar o utilizador principal na BD (se ainda não existir)
    db.save_jogador(user_id, user.full_name)

    parceiro = db.get_jogador_by_phone(phone_number)

    if parceiro:
        parceiro_id, parceiro_nome, _ = parceiro
        sucesso_user = db.inscrever_jogador(user_id, torneio_id, "Esquerda")
        sucesso_parceiro = db.inscrever_jogador(parceiro_id, torneio_id, "Direita")
        if sucesso_user and sucesso_parceiro:
            await update.message.reply_text(f"Tu e o teu parceiro {parceiro_nome} foram inscritos com sucesso!")
        else:
            await update.message.reply_text("Erro na inscrição. Talvez tu ou o teu parceiro já estejam inscritos.")
    else:
        # Parceiro não está registado — inscrever só o utilizador principal
        # e guardar nota do parceiro como nome no placeholder (sem telegram_id real)
        sucesso = db.inscrever_jogador(user_id, torneio_id, "Esquerda")
        if sucesso:
            await update.message.reply_text(
                f"Ficaste inscrito! O teu parceiro com o número {phone_number} ainda não está registado no bot. "
                f"Pede-lhe que use /start para se registar e depois inscreva-se."
            )
        else:
            await update.message.reply_text("Ocorreu um erro. Talvez já estejas inscrito.")

    await send_tournament_update_to_group(context, torneio_id)
    return ConversationHandler.END