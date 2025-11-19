# Bot Discord — Deploy no Render

Este repositório contém um bot Discord em `discord.py` preparado para deploy no Render.

O que eu já fiz:
- Removi o token hard-coded do código e agora o bot usa a variável de ambiente `DISCORD_TOKEN`.
- Adicionei `requirements.txt` com dependências básicas.
- Adicionei `.gitignore` para ignorar o arquivo `economia.json` e arquivos sensíveis.

Passo-a-passo para deploy no Render (rápido):

1) No GitHub: verifique que o repositório está com as mudanças commitadas e pushadas.

2) No painel do Render:
   - Clique em "New" → "Web Service" (um "Background Worker" também funciona, mas Web Service é simples).
   - Conecte sua conta ao GitHub e selecione o repositório.
   - Branch: `main` (ou a branch que você usa).
   - Environment: `Python 3`.
   - Start Command: `python bot.py`.

3) Adicione variáveis de ambiente no Render (Settings → Environment):
   - `DISCORD_TOKEN` → o token do bot (marque como secreto).

4) Deploy: inicie o deploy. Verifique os logs (Logs → Live) para ver se o bot conecta corretamente.

Observações de segurança importantes:
- O token antigo estava commitado no arquivo antes das alterações. Você deve rotacionar (regenerar) o token no portal do Discord Developer e substituir a variável `DISCORD_TOKEN` no Render pelo novo token.
- Nunca compartilhe o token publicamente.

Comandos locais úteis:

```bash
# Instalar dependências localmente
python -m pip install -r requirements.txt

# Rodar localmente (defina a variável ou use .env localmente)
export DISCORD_TOKEN="seu_token_aqui"
python bot.py
```

Se quiser, eu também faço o commit e dou push das mudanças para você (vou tentar agora) e, se desejar, posso criar um `render.yaml` com configurações padrão para deploy automático.
