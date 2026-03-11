# Gestor de Torneios de Padel 🎾

Este projeto é um Bot de Telegram para gerir torneios de Padel, permitindo inscrições de jogadores por nível.

## Funcionalidades

- **Registo de Jogadores**: Definição de nível (L2, L3, L4, L5).
- **Torneios**: Visualização de torneios e vagas disponíveis.
- **Inscrição**: Validação de nível e vagas.
- **Unsubscribe**: Possibilidade de cancelar inscrição.
- **Admin**: Painel para criar/apagar torneios.

## Como Iniciar

1. Certifica-te que tens o Python instalado.
2. Instala as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Configura o ficheiro `.env`:
   - `BOT_TOKEN`: O token do teu bot.
   - `ADMIN_ID`: O teu ID de Telegram (usa o comando `/myid` no bot para descobrir).
4. Executa o bot:
   ```bash
   python bot.py
   ```

## Comandos de Admin

Se tiveres o `ADMIN_ID` configurado, verás um botão "Painel Admin" no menu principal.
Podes também usar comandos diretos:
- `/criartorneio <Nome> <Nivel> <Vagas>`
- `/apagartorneio <ID>`
