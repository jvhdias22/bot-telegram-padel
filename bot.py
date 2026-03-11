import os
import logging
from dotenv import load_dotenv

# Carregar .env ANTES de importar handlers (que lê ADMIN_ID no topo)
load_dotenv()

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import database as db
import handlers

# Configuração de Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    TOKEN = os.getenv('BOT_TOKEN')
    
    if not TOKEN:
        print("ERRO: BOT_TOKEN não encontrado no ficheiro .env")
        return

    # Inicializar Base de Dados
    db.init_db()

    # Criar a Aplicação
    app = Application.builder().token(TOKEN).build()

    # Handlers - Comandos
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("criartorneio", handlers.comando_criar_torneio))
    app.add_handler(CommandHandler("apagartorneio", handlers.comando_apagar_torneio))
    app.add_handler(CommandHandler("myid", handlers.my_id))
    
    # Handlers - Menus e Navegação
    app.add_handler(CallbackQueryHandler(handlers.start, pattern='^menu_principal$'))
    app.add_handler(CallbackQueryHandler(handlers.ver_torneios, pattern='^ver_torneios$'))
    app.add_handler(CallbackQueryHandler(handlers.detalhe_torneio, pattern='^detalhe_'))
    app.add_handler(CallbackQueryHandler(handlers.realizar_inscricao, pattern=r'^inscrever_\d+$'))
    app.add_handler(CallbackQueryHandler(handlers.inscrever_suplente, pattern='^inscrever_suplente_'))
    app.add_handler(CallbackQueryHandler(handlers.inscricao_individual, pattern='^inscricao_individual_'))
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handlers.inscricao_parceiro, pattern='^inscricao_parceiro_')],
        states={
            handlers.AGUARDAR_NUMERO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.aguardar_numero)],
        },
        fallbacks=[CommandHandler('start', handlers.start)],
    )
    app.add_handler(conv_handler)

    app.add_handler(CallbackQueryHandler(handlers.realizar_inscricao_posicao, pattern='^inscricao_posicao_'))
    app.add_handler(CallbackQueryHandler(handlers.sair_torneio, pattern='^sair_'))
    app.add_handler(CallbackQueryHandler(handlers.ajuda, pattern='^ajuda$'))
    app.add_handler(CallbackQueryHandler(handlers.admin_panel, pattern='^admin_panel$'))

    # Error Handler
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logging.error("Exception while handling an update:", exc_info=context.error)
    
    app.add_error_handler(error_handler)

    print("🤖 Bot de Padel Iniciado! (Ctrl+C para parar)")
    app.run_polling()

if __name__ == '__main__':
    main()
