
from discord.ext import commands
import json
import os
import random
import time
import asyncio


# --- Configuração do Bot e Intents ---
# É crucial habilitar message_content e members (para comandos de rank/membro)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

# Define o prefixo do comando (ex: !saldo)
bot = commands.Bot(command_prefix='!', intents=intents)

# --- Configurações de Economia e Cassino ---
DATA_FILE = 'economia.json'
DAILY_COINS = 500
DAILY_COOLDOWN = 86400  # 24 horas em segundos

CASINO_COOLDOWN = 3
JACKPOT_EMOJI = "💎"

# CONFIGURAÇÃO DA FAZENDA (FARM)
MAX_PLOTS = 10 # 10 LOTES
FARM_ITEMS = {
    "trigo": {"emoji": "🌾", "growth_time": 0, "price": 100},
    "alface": {"emoji": "🥬", "growth_time": 0, "price": 300},
    "tomate": {"emoji": "🍅", "growth_time": 0, "price": 600},
    "cenoura": {"emoji": "🥕", "growth_time": 0, "price": 1200}
}

# --- ESTADO TEMPORÁRIO DE PROPOSTAS DE CASAMENTO ---
# {propositor_id: {target_id: ID do usuário pedido, channel_id: ID do canal, timestamp: float}}
marriage_proposals = {} 

# ----------------------------------------------------
# 📂 FUNÇÕES DE GERENCIAMENTO DE DADOS (MANTIDAS INALTERADAS)
# ----------------------------------------------------

def load_data():
    """Carrega os dados de economia do arquivo JSON."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_data(data):
    """Salva os dados de economia no arquivo JSON."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_user_data(user_id):
    """Obtém e inicializa os dados do usuário, garantindo a estrutura da fazenda/casamento."""
    data = load_data()
    user_id_str = str(user_id)
    
    if user_id_str not in data:
        data[user_id_str] = {"balance": 0, "last_daily": 0}
        
    # Garante estrutura da fazenda
    if 'farm' not in data[user_id_str]:
        data[user_id_str]['farm'] = {
            'plots': [{'item': None, 'planted_at': 0, 'ready_at': 0} for _ in range(MAX_PLOTS)],
            'inventory': {}
        }
    
    # Garante que a quantidade de plots esteja correta
    current_plots = data[user_id_str]['farm']['plots']
    while len(current_plots) < MAX_PLOTS:
        current_plots.append({'item': None, 'planted_at': 0, 'ready_at': 0})
    data[user_id_str]['farm']['plots'] = current_plots[:MAX_PLOTS]
    
    save_data(data)
    return data[user_id_str]

def get_user_balance(user_id):
    """Retorna o saldo de um usuário ou 0 se ele for novo."""
    user_data = get_user_data(user_id)
    return user_data['balance']

def update_user_balance(user_id, amount):
    """Adiciona ou subtrai um valor do saldo do usuário."""
    data = load_data()
    user_id_str = str(user_id)
    
    get_user_data(user_id) # Garante inicialização
        
    data[user_id_str]['balance'] += amount
    save_data(data)
    return data[user_id_str]['balance']

def get_last_daily(user_id):
    """Retorna o timestamp do último daily."""
    user_data = get_user_data(user_id)
    return user_data.get('last_daily', 0)

def set_last_daily(user_id):
    """Atualiza o timestamp do último daily para agora."""
    data = load_data()
    user_id_str = str(user_id)
    get_user_data(user_id) # Garante inicialização
    data[user_id_str]['last_daily'] = time.time()
    save_data(data)

# --- FUNÇÕES AUXILIARES DE CASAMENTO ---

def set_marriage(user1_id, user2_id):
    """Registra o casamento entre dois usuários no banco de dados."""
    data = load_data()
    user1_str = str(user1_id)
    user2_str = str(user2_id)
    
    get_user_data(user1_id)
    get_user_data(user2_id)
    
    data[user1_str]['spouse'] = user2_id
    data[user2_str]['spouse'] = user1_id
    save_data(data)

def is_married(user_id):
    """Verifica se o usuário está casado."""
    user_data = get_user_data(user_id)
    # A verificação é mais robusta se garantir que o spouse existe e é diferente de None.
    return user_data.get('spouse') is not None

def get_spouse_id(user_id):
    """Retorna o ID do cônjuge, ou None."""
    user_data = get_user_data(user_id)
    return user_data.get('spouse')

# ----------------------------------------------------
# ⚡ EVENTOS DO BOT
# ----------------------------------------------------

@bot.event
async def on_ready():
    print(f'🤖 Bot de Economia online como {bot.user}')
    print(f'Prefixo de comando: {bot.command_prefix}')

# ----------------------------------------------------
# 💰 COMANDOS DE ECONOMIA
# ----------------------------------------------------

@bot.command(name='saldo', aliases=['bal'], help='Mostra seu saldo atual de moedas.')
async def balance(ctx, member: discord.Member = None):
    target = member or ctx.author
    saldo = get_user_balance(target.id)
    
    embed = discord.Embed(
        title=f'💰 Saldo de {target.display_name}',
        description=f'Você possui **{saldo:,} Moedas** no banco.',
        color=discord.Color.gold()
    )
    # Opcional: Adiciona a imagem de avatar se o objeto avatar.url existir
    if target.avatar and target.avatar.url:
        embed.set_thumbnail(url=target.avatar.url) 
    
    await ctx.send(embed=embed)

@bot.command(name='daily', help='Resgate sua recompensa diária de moedas.')
async def daily(ctx):
    user_id = ctx.author.id
    last_daily = get_last_daily(user_id)
    tempo_decorrido = time.time() - last_daily
    
    if tempo_decorrido >= DAILY_COOLDOWN:
        novo_saldo = update_user_balance(user_id, DAILY_COINS)
        set_last_daily(user_id)
        
        embed = discord.Embed(
            title='🎉 Recompensa Diária Resgatada!',
            description=f'Você ganhou **{DAILY_COINS} Moedas**.',
            color=discord.Color.green()
        )
        embed.add_field(name='Saldo Atual', value=f'**{novo_saldo:,} Moedas**', inline=False)
        embed.set_footer(text=f'Próximo Daily disponível em 24h. | Usuário: {ctx.author.display_name}')
        
        await ctx.send(embed=embed)
    else:
        tempo_restante = DAILY_COOLDOWN - tempo_decorrido
        horas = int(tempo_restante // 3600)
        minutos = int((tempo_restante % 3600) // 60)
        segundos = int(tempo_restante % 60)
        
        embed = discord.Embed(
            title='⏰ Calma lá!',
            description=f'O Daily já foi resgatado hoje.',
            color=discord.Color.red()
        )
        embed.add_field(name='Tempo Restante', value=f'**{horas}h {minutos}m {segundos}s**', inline=False)
        embed.set_footer(text='Aguarde o cooldown para resgatar novamente.')
        
        await ctx.send(embed=embed)

@bot.command(name='trabalhar', aliases=['work'], help='Ganhe moedas trabalhando.')
@commands.cooldown(1, 3600, commands.BucketType.user) 
async def trabalhar(ctx):
    profissao = random.choice(['Programador de Bot', 'Vendedor de Pastel', 'Taxista', 'Entregador de Pizza'])
    ganho = random.randint(150, 400)
    
    novo_saldo = update_user_balance(ctx.author.id, ganho)
    
    embed = discord.Embed(
        title='💼 Trabalhando Duro!',
        description=f'Você conseguiu um trabalho de **{profissao}**.',
        color=discord.Color.blue()
    )
    embed.add_field(name='Ganho', value=f'**+{ganho} Moedas**', inline=True)
    embed.add_field(name='Novo Saldo', value=f'**{novo_saldo:,} Moedas**', inline=True)
    embed.set_footer(text='Você só pode trabalhar novamente em 1 hora.')
    
    await ctx.send(embed=embed)

@trabalhar.error
async def trabalhar_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        tempo_restante = error.retry_after
        minutos = int(tempo_restante // 60)
        segundos = int(tempo_restante % 60)
        
        embed = discord.Embed(
            title='❌ Você está exausto!',
            description='Você precisa descansar um pouco antes de trabalhar de novo.',
            color=discord.Color.dark_red()
        )
        embed.add_field(name='Tempo Restante', value=f'**{minutos}m {segundos}s**', inline=False)
        await ctx.send(embed=embed)

@bot.command(name='lavar', help='Lave alguns carros e ganhe moedas (cooldown mais curto).')
@commands.cooldown(1, 600, commands.BucketType.user) 
async def lavar(ctx):
    ganho = random.randint(50, 150)
    
    novo_saldo = update_user_balance(ctx.author.id, ganho)
    
    embed = discord.Embed(
        title='🧼 Serviço de Lavagem!',
        description='Você lavou alguns carros e o cliente pagou bem.',
        color=discord.Color.teal()
    )
    embed.add_field(name='Ganho', value=f'**+{ganho} Moedas**', inline=True)
    embed.add_field(name='Novo Saldo', value=f'**{novo_saldo:,} Moedas**', inline=True)
    embed.set_footer(text='Próximo serviço em 10 minutos.')
    
    await ctx.send(embed=embed)

@lavar.error
async def lavar_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        tempo_restante = error.retry_after
        minutos = int(tempo_restante // 60)
        segundos = int(tempo_restante % 60)
        
        embed = discord.Embed(
            title='❌ Mãos Cansadas!',
            description='Você não consegue mais esfregar! Precisa de um descanso.',
            color=discord.Color.dark_red()
        )
        embed.add_field(name='Tempo Restante', value=f'**{minutos}m {segundos}s**', inline=False)
        await ctx.send(embed=embed)

@bot.command(name='rank', help='Exibe o ranking dos 10 usuários mais ricos.')
async def rank(ctx):
    data = load_data()
    
    leaderboard = []
    for user_id_str, user_data in data.items():
        if 'balance' in user_data and user_data.get('balance', 0) > 0:
            try:
                # Tenta buscar o membro no guild primeiro
                user = ctx.guild.get_member(int(user_id_str)) 
                # Se não encontrar no guild, busca globalmente
                if not user:
                    user = await bot.fetch_user(int(user_id_str))
                    
                leaderboard.append({
                    'name': user.display_name,
                    'balance': user_data['balance']
                })
            except discord.NotFound:
                leaderboard.append({
                    'name': f'Usuário Desconhecido ({user_id_str})',
                    'balance': user_data['balance']
                })

    leaderboard.sort(key=lambda x: x['balance'], reverse=True)
    top_10 = leaderboard[:10]

    rank_msg = []
    for i, entry in enumerate(top_10):
        emoji = {0: '🥇', 1: '🥈', 2: '🥉'}.get(i, '🔹')
        # Formata o número com separador de milhares
        balance_formatted = f'{entry["balance"]:,}'.replace(',', '.')
        rank_msg.append(f'{emoji} **{i+1}**. {entry["name"]} - **{balance_formatted}** Moedas')
        
    embed = discord.Embed(
        title='👑 TOP 10 Mais Ricos do Servidor',
        description='\n'.join(rank_msg) if rank_msg else 'Ninguém no ranking ainda! Comece usando `!daily`!',
        color=discord.Color.blue()
    )
    embed.set_footer(text='Mostrando os usuários com maior saldo de moedas.')
    
    await ctx.send(embed=embed)


# ----------------------------------------------------
# 🎰 COMANDOS DE CASSINO
# ----------------------------------------------------

@bot.command(name='aposta', aliases=['bet'], help='Aposte um valor e tente dobrá-lo!')
@commands.cooldown(1, 15, commands.BucketType.user) # Cooldown de 15 segundos entre apostas
async def aposta(ctx, valor: int):
    user_id = ctx.author.id
    saldo_atual = get_user_balance(user_id)
    
    if valor <= 0:
        await ctx.send('❌ Você deve apostar um valor positivo.')
        return
        
    if valor > saldo_atual:
        await ctx.send('❌ Você não tem saldo suficiente para esta aposta.')
        return

    # 1. Tira o dinheiro do usuário imediatamente
    update_user_balance(user_id, -valor)
    
    embed_iniciar = discord.Embed(
        title='🎲 Aposta Recebida!',
        description=f'**{valor:,} Moedas** foram colocadas no jogo. O resultado sai em **10 segundos**!',
        color=discord.Color.orange()
    )
    embed_iniciar.set_footer(text='Boa sorte! O resultado é gerado aleatoriamente.')
    
    mensagem_status = await ctx.send(embed=embed_iniciar)
    
    # Simula o tempo de espera
    await asyncio.sleep(10)
    
    # 2. Gera o resultado (Chance de 50% de vitória)
    if random.choice([True, False]): 
        # Ganhou: Dobra a aposta (devolve o valor + o valor da aposta)
        ganho_total = valor * 2
        lucro = valor
        novo_saldo = update_user_balance(user_id, ganho_total)
        
        embed_resultado = discord.Embed(
            title='✅ VITÓRIA!',
            description=f'O cassino sorriu para você! Você ganhou **{ganho_total:,} Moedas**.',
            color=discord.Color.green()
        )
        embed_resultado.add_field(name='Lucro', value=f'+{lucro:,} Moedas', inline=True)
        embed_resultado.add_field(name='Novo Saldo', value=f'{novo_saldo:,} Moedas', inline=True)
        embed_resultado.set_footer(text=f'Parabéns, {ctx.author.display_name}!')
        
    else:
        # Perdeu: O valor já foi retirado na etapa 1
        novo_saldo = get_user_balance(user_id) # Pega o saldo após a perda
        
        embed_resultado = discord.Embed(
            title='❌ DERROTA!',
            description=f'Azar no jogo... Você perdeu **{valor:,} Moedas**.',
            color=discord.Color.red()
        )
        embed_resultado.add_field(name='Perda', value=f'-{valor:,} Moedas', inline=True)
        embed_resultado.add_field(name='Novo Saldo', value=f'{novo_saldo:,} Moedas', inline=True)
        embed_resultado.set_footer(text='Tente novamente! Lembre-se de jogar com responsabilidade.')

    # 3. Edita a mensagem para mostrar o resultado final
    await mensagem_status.edit(embed=embed_resultado)

@aposta.error
async def aposta_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        tempo_restante = error.retry_after
        embed_cooldown = discord.Embed(
            title='⏳ Cooldown Ativo',
            description=f'Aguarde um pouco antes de apostar novamente. Tempo restante: **{int(tempo_restante)}s**.',
            color=discord.Color.dark_red()
        )
        await ctx.send(embed=embed_cooldown)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('❌ Formato correto: `!aposta <valor>`')
    elif isinstance(error, commands.BadArgument):
        await ctx.send('❌ O valor da aposta deve ser um número inteiro.')

@bot.command(name='cassino', aliases=['slots'], help=f'Aposte e gire a máquina caça-níqueis. Cooldown de {CASINO_COOLDOWN}s.')
@commands.cooldown(1, CASINO_COOLDOWN, commands.BucketType.user)
async def cassino(ctx, valor: int):
    user_id = ctx.author.id
    saldo_atual = get_user_balance(user_id)
    
    if valor <= 0:
        await ctx.send('❌ Você deve apostar um valor positivo.', delete_after=5)
        return
        
    if valor > saldo_atual:
        await ctx.send('❌ Você não tem saldo suficiente para esta aposta.', delete_after=5)
        return
        
    # Tira o dinheiro do usuário imediatamente
    update_user_balance(user_id, -valor)
    
    emojis = [JACKPOT_EMOJI, "💰", "🍒", "🍀", "🍋", "💔"] 
    
    # 1. Gira a máquina 3 vezes
    results = random.choices(emojis, k=3)
    results_str = " | ".join(results)
    
    # 2. Verifica as condições de vitória
    ganho_moedas = 0 
    titulo = '❌ AZAR!'
    cor = discord.Color.red()
    
    # Função auxiliar para verificar se há 2 ou mais iguais
    def check_two_equal(res):
        counts = {}
        for item in res:
            counts[item] = counts.get(item, 0) + 1
        return max(counts.values()) if counts else 0
    
    # --- VERIFICAÇÃO DE VITÓRIA (do maior para o menor prêmio) ---
    
    num_iguais = check_two_equal(results)
    multiplicador = 0
    
    # Condição 1: JACKPOT (3 Diamantes)
    if results.count(JACKPOT_EMOJI) == 3:
        multiplicador = 10
        titulo = '✨ JACKPOT! (10x)'
        cor = discord.Color.gold()
        
    # Condição 2: TRIPLO (3 de qualquer outro emoji)
    elif num_iguais == 3:
        multiplicador = 8 # Novo prêmio para o triplo
        titulo = f'✅ TRIPLO! (8x)'
        cor = discord.Color.green()

    # Condição 3: DOIS IGUAIS
    elif num_iguais == 2:
        multiplicador = 5 # Seu prêmio de 5x para dois iguais
        titulo = f'🔥 DOBRA FORTE! (5x)'
        cor = discord.Color.blue()
        
    # --- FIM DA VERIFICAÇÃO ---
    
    ganho_moedas = valor * multiplicador
        
    # 3. Calcula resultado final e atualiza saldo
    
    if ganho_moedas > 0:
        # Adiciona o valor total que ele ganhou (que já inclui a aposta)
        update_user_balance(user_id, ganho_moedas) 
        
    lucro = ganho_moedas - valor # Lucro pode ser negativo (perda) ou positivo
    novo_saldo = get_user_balance(user_id)
    
    # 4. Envia o Embed
    embed = discord.Embed(
        title=titulo,
        description=f'Máquina: **{results_str}**',
        color=cor
    )
    embed.add_field(name='Aposta', value=f'-{valor:,} Moedas', inline=True)
    embed.add_field(name='Resultado', 
                    # Mostra + para lucro e apenas o número (negativo) para perda
                    value=f'**+{lucro:,} Moedas**' if lucro > 0 else f'**{lucro:,} Moedas**', 
                    inline=True)
    embed.add_field(name='Novo Saldo', value=f'{novo_saldo:,} Moedas', inline=False)
    
    await ctx.send(embed=embed)

@cassino.error
async def cassino_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        tempo_restante = error.retry_after
        await ctx.send(f'⏳ Espere um pouco para o próximo giro. Cooldown: **{int(tempo_restante)}s**.', delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('❌ Formato correto: `!cassino <valor>`')
    elif isinstance(error, commands.BadArgument):
        await ctx.send('❌ O valor da aposta deve ser um número inteiro.')

# ----------------------------------------------------
# 💸 COMANDOS DE TRANSFERÊNCIA
# ----------------------------------------------------

@bot.command(name='transferir', aliases=['pagar', 'pay'], help='Transfere um valor do seu saldo para outro usuário.')
async def transferir(ctx, membro: discord.Member, valor: int):
    pagador_id = ctx.author.id
    recebedor_id = membro.id
    
    if valor <= 0:
        await ctx.send('❌ O valor a ser transferido deve ser positivo.')
        return

    if pagador_id == recebedor_id:
        await ctx.send('❌ Você não pode transferir para si mesmo.')
        return

    saldo_pagador = get_user_balance(pagador_id)
    
    if valor > saldo_pagador:
        await ctx.send('❌ Você não tem saldo suficiente para fazer esta transferência.')
        return
        
    # 1. Retira o valor do pagador
    update_user_balance(pagador_id, -valor)
    novo_saldo_pagador = get_user_balance(pagador_id)
    
    # 2. Adiciona o valor ao recebedor
    novo_saldo_recebedor = update_user_balance(recebedor_id, valor)
    
    embed = discord.Embed(
        title='💸 Transferência Concluída!',
        description=f'**{ctx.author.display_name}** transferiu **{valor:,} Moedas** para **{membro.display_name}**.',
        color=discord.Color.purple()
    )
    embed.add_field(name=f'Seu novo saldo ({ctx.author.display_name})', 
                    value=f'**{novo_saldo_pagador:,}** Moedas', inline=True)
    embed.add_field(name=f'Saldo de {membro.display_name}', 
                    value=f'**{novo_saldo_recebedor:,}** Moedas', inline=True)
    embed.set_footer(text='Obrigado por usar o sistema de economia!')
    
    await ctx.send(embed=embed)

@transferir.error
async def transferir_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('❌ Formato correto: `!transferir <@membro> <valor>`')
    elif isinstance(error, commands.BadArgument):
        await ctx.send('❌ Verifique se você marcou um membro e digitou um valor válido.')

# ----------------------------------------------------
# 🔒 COMANDOS DE ADMINISTRAÇÃO
# ----------------------------------------------------

@bot.command(name='addsaldo', help='[ADM] Adiciona saldo à conta de um usuário.')
@commands.has_permissions(administrator=True)
async def adds_saldo(ctx, membro: discord.Member, valor: int): 
    if valor <= 0:
        await ctx.send('❌ O valor a ser adicionado deve ser positivo.')
        return
        
    novo_saldo = update_user_balance(membro.id, valor)
    
    embed = discord.Embed(
        title='➕ Saldo Adicionado (ADM)',
        description=f'O administrador **{ctx.author.display_name}** adicionou **{valor:,} Moedas** à conta de {membro.display_name}.',
        color=discord.Color.dark_green()
    )
    # A linha redundante foi removida daqui
    embed.add_field(name='Novo Saldo do Usuário', value=f'**{novo_saldo:,} Moedas**', inline=False)
    
    await ctx.send(embed=embed)

@adds_saldo.error
async def adds_saldo_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('❌ Formato correto: `!addsaldo <@membro> <valor>`')
    elif isinstance(error, commands.BadArgument):
        await ctx.send('❌ Verifique se você marcou um membro e digitou um valor válido.')
    elif isinstance(error, commands.MissingPermissions): # Corrigido: usa MissingPermissions
        await ctx.send('🚫 **ACESSO NEGADO:** Você precisa de permissão de Administrador para usar este comando.')


@bot.command(name='retirarsaldo', help='[ADM] Retira saldo da conta de um usuário.')
@commands.has_permissions(administrator=True)
async def retirars_saldo(ctx, membro: discord.Member, valor: int):
    if valor <= 0:
        await ctx.send('❌ O valor a ser retirado deve ser positivo.')
        return
        
    # Retirar saldo é o mesmo que adicionar um valor negativo
    novo_saldo = update_user_balance(membro.id, -valor) 
    
    embed = discord.Embed(
        title='➖ Saldo Retirado (ADM)',
        description=f'O administrador **{ctx.author.display_name}** retirou **{valor:,} Moedas** da conta de {membro.display_name}.',
        color=discord.Color.dark_red()
    )
    embed.add_field(name='Novo Saldo do Usuário', value=f'**{novo_saldo:,} Moedas**', inline=False)
    
    await ctx.send(embed=embed)

@retirars_saldo.error
async def retirars_saldo_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('❌ Formato correto: `!retirarsaldo <@membro> <valor>`')
    elif isinstance(error, commands.BadArgument):
        await ctx.send('❌ Verifique se você marcou um membro e digitou um valor válido.')
    elif isinstance(error, commands.MissingPermissions): # Corrigido: usa MissingPermissions
        await ctx.send('🚫 **ACESSO NEGADO:** Você precisa de permissão de Administrador para usar este comando.')


# ----------------------------------------------------
# 🧑‍🌾 COMANDOS DA FAZENDA
# ----------------------------------------------------

@bot.command(name='farm', help=f'Planta um item em um dos seus {MAX_PLOTS} lotes. Crescimento instantâneo.')
async def farm(ctx, item_name: str = None):
    user_id = ctx.author.id
    data = load_data()
    user_data = get_user_data(user_id)
    
    if not item_name or item_name.lower() not in FARM_ITEMS:
        lista_itens = ", ".join([f'{k} ({v["emoji"]})' for k, v in FARM_ITEMS.items()])
        await ctx.send(f'❌ Item inválido! Use: `!farm <item>`. Itens disponíveis: {lista_itens}')
        return

    item_key = item_name.lower()
    item_info = FARM_ITEMS[item_key]
    item_full_name = f'{item_key.capitalize()} {item_info["emoji"]}'
    
    plots = user_data['farm']['plots']
    empty_plot_index = -1
    
    for i, plot in enumerate(plots):
        if plot['item'] is None:
            empty_plot_index = i
            break
            
    if empty_plot_index == -1:
        await ctx.send(f'❌ Todos os seus {MAX_PLOTS} lotes estão ocupados! Use `!colher` para liberar.')
        return

    current_time = int(time.time())
    ready_time = current_time + item_info['growth_time'] # Será instantâneo (growth_time=0)
    
    plots[empty_plot_index] = {
        'item': item_full_name,
        'planted_at': current_time,
        'ready_at': ready_time
    }
    
    data[str(user_id)]['farm']['plots'] = plots
    save_data(data)

    embed = discord.Embed(
        title=f'🌱 Plantado com Sucesso! (INSTANTÂNEO)',
        description=f'Você plantou **{item_full_name}** no Lote **#{empty_plot_index + 1}**.',
        color=discord.Color.brand_green()
    )
    embed.add_field(name='Status', value='**Pronto para Colheita IMEDIATAMENTE!**', inline=False)
    
    await ctx.send(embed=embed)


@bot.command(name='colher', help='Colhe os itens que já cresceram e os adiciona ao seu inventário.')
async def colher(ctx):
    user_id = ctx.author.id
    data = load_data()
    user_data = get_user_data(user_id)
    plots = user_data['farm']['plots']
    inventory = user_data['farm']['inventory']
    
    colhidos = {}
    current_time = int(time.time())
    
    for i in range(len(plots)):
        plot = plots[i]
        
        if plot['item'] and current_time >= plot['ready_at']:
            item_name = plot['item']
            # Garante que a chave existe antes de incrementar
            if item_name in inventory:
                 inventory[item_name] = inventory[item_name] + 1
            else:
                 inventory[item_name] = 1
            
            colhidos[item_name] = colhidos.get(item_name, 0) + 1
            plots[i] = {'item': None, 'planted_at': 0, 'ready_at': 0}
        
    data[str(user_id)]['farm']['plots'] = plots
    data[str(user_id)]['farm']['inventory'] = inventory
    save_data(data)
    
    if not colhidos:
        await ctx.send('❌ Você não tem nada plantado ou pronto para colheita. Use `!farm` primeiro!')
        return

    colheita_str = '\n'.join([f'1x **{k}**' for k, v in colhidos.items()])
    
    embed = discord.Embed(
        title='🧺 Colheita Completa!',
        description=f'Você colheu os seguintes itens e os adicionou ao seu inventário:\n{colheita_str}',
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)


@bot.command(name='vd', aliases=['vender'], help='Vende um item do seu inventário. Ex: !vd trigo 5')
async def vd(ctx, item_name: str = None, quantidade: int = 1):
    user_id = ctx.author.id
    data = load_data()
    user_data = get_user_data(user_id)
    inventory = user_data['farm']['inventory']
    
    if quantidade <= 0:
        await ctx.send('❌ A quantidade a ser vendida deve ser positiva.')
        return
        
    # Lógica para limpar o nome do item e checar se é um item de fazenda
    item_key_clean = item_name.lower().split()[0] if item_name else None
    
    if item_key_clean not in FARM_ITEMS:
        await ctx.send('❌ Item de fazenda inválido. Verifique a ortografia.')
        return

    item_info = FARM_ITEMS[item_key_clean]
    item_full_name = f'{item_key_clean.capitalize()} {item_info["emoji"]}'
    
    if item_full_name not in inventory or inventory[item_full_name] < quantidade:
        estoque = inventory.get(item_full_name, 0)
        await ctx.send(f'❌ Você só tem **{estoque}** de {item_full_name} no inventário.')
        return
        
    preco_unitario = item_info['price']
    ganho_total = preco_unitario * quantidade
    
    inventory[item_full_name] -= quantidade
    if inventory[item_full_name] == 0:
        del inventory[item_full_name] 
        
    novo_saldo = update_user_balance(user_id, ganho_total)
    
    data[str(user_id)]['farm']['inventory'] = inventory
    save_data(data)

    embed = discord.Embed(
        title='💸 Venda Realizada!',
        description=f'Você vendeu **{quantidade}x {item_full_name}**.',
        color=discord.Color.teal()
    )
    embed.add_field(name='Ganho Total', value=f'**+{ganho_total:,} Moedas**', inline=True)
    embed.add_field(name='Novo Saldo', value=f'**{novo_saldo:,} Moedas**', inline=True)
    
    await ctx.send(embed=embed)


# ----------------------------------------------------
# 👰‍♀️ COMANDOS DE CASAMENTO
# ----------------------------------------------------

@bot.command(name='casar', aliases=['propor'], help='Pede um membro em casamento.')
async def casar(ctx, membro: discord.Member):
    propositor_id = ctx.author.id
    target_id = membro.id
    
    if is_married(propositor_id):
        await ctx.send(f'❌ {ctx.author.mention}, você já está casado(a)! Use `!divorciar` primeiro.')
        return

    if is_married(target_id):
        await ctx.send(f'❌ {membro.mention} já está casado(a) com outra pessoa.')
        return
        
    if propositor_id == target_id:
        await ctx.send(f'❌ {ctx.author.mention}, você não pode se casar consigo mesmo(a).')
        return

    # Registra a proposta no estado temporário (válida por 60 segundos)
    marriage_proposals[propositor_id] = {
        'target_id': target_id,
        'channel_id': ctx.channel.id,
        'timestamp': time.time()
    }

    embed = discord.Embed(
        title='💖 Pedido de Casamento!',
        description=f'{membro.mention}, **{ctx.author.display_name}** te pediu em casamento!',
        color=discord.Color.red()
    )
    embed.set_footer(text=f'Para aceitar, {membro.display_name} deve digitar !aceitar em até 60 segundos neste canal.')
    
    await ctx.send(embed=embed)

@bot.command(name='aceitar', help='Aceita um pedido de casamento pendente.')
async def aceitar(ctx):
    aceitante_id = ctx.author.id
    
    if is_married(aceitante_id):
        await ctx.send(f'❌ {ctx.author.mention}, você já está casado(a)!')
        return
        
    propositor_id = None
    
    # 1. Procura por uma proposta onde o aceitante é o alvo
    for p_id, proposal in marriage_proposals.items():
        if proposal['target_id'] == aceitante_id and proposal['channel_id'] == ctx.channel.id:
            propositor_id = p_id
            break
            
    if not propositor_id:
        await ctx.send('❌ Não há nenhum pedido de casamento pendente para você neste canal.', delete_after=10)
        return
        
    # 2. Verifica se a proposta expirou (tempo de 60s)
    if time.time() - marriage_proposals[propositor_id]['timestamp'] > 60:
        await ctx.send('❌ O pedido de casamento expirou. Peça para o proponente tentar novamente.', delete_after=10)
        del marriage_proposals[propositor_id]
        return
        
    # 3. Finaliza o casamento (CORRIGIDO)
    set_marriage(propositor_id, aceitante_id)
    # Tenta obter o membro do servidor ou o usuário global
    propositor_member = ctx.guild.get_member(propositor_id) or bot.get_user(propositor_id)

    # Conclui o envio da mensagem
    await ctx.send(f'🔔 **CASADOS!** 🔔\nParabéns, {propositor_member.mention} e {ctx.author.mention}! Vocês agora estão casados.')
    
    # Remove a proposta do estado temporário
    del marriage_proposals[propositor_id]




@bot.command(name='divorciar', help='Inicia o processo de divórcio (requer confirmação).')
async def divorciar(ctx):
    user_id = ctx.author.id
    
    if not is_married(user_id):
        await ctx.send('❌ Você não é casado(a).', delete_after=10)
        return
        
    spouse_id = get_spouse_id(user_id)
    spouse_member = ctx.guild.get_member(spouse_id) or bot.get_user(spouse_id)

    def check_confirm(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'sim'

    await ctx.send(f'⚠️ **CONFIRMAÇÃO DE DIVÓRCIO:** Você realmente deseja se divorciar de **{spouse_member.display_name}**? Digite `sim` para confirmar em 15 segundos.')

    try:
        await bot.wait_for('message', check=check_confirm, timeout=15.0)
        
        # Processa o divórcio
        set_marriage(user_id, None) 
        set_marriage(spouse_id, None)
        
        await ctx.send(f'💔 Divórcio finalizado. {ctx.author.mention} e {spouse_member.mention} não estão mais casados(as).')

    except asyncio.TimeoutError:
        await ctx.send('Divórcio cancelado. Confirmação não recebida a tempo.')

        # --- CONFIGURAÇÃO DO SHIP ---
BAR_BLOCK = "█"
EMPTY_BLOCK = "░"
BAR_LENGTH = 10

def calculate_ship_score(id1, id2):
    """Calcula uma pontuação de 0 a 100 de forma determinística."""
    # Garante que a ordem dos IDs não mude o resultado
    sorted_ids = tuple(sorted([id1, id2]))
    # Converte os IDs em uma string para usar como seed
    seed = f"{sorted_ids[0]}{sorted_ids[1]}".encode('utf-8')
    
    # Gera um hash SHA-256 da seed
    hash_object = hashlib.sha256(seed)
    hex_dig = hash_object.hexdigest()
    
    # Pega os primeiros 4 caracteres do hash, converte para inteiro, e mapeia para 0-100
    score_seed = int(hex_dig[:4], 16) 
    return score_seed % 101 # Score de 0 a 100

def get_ship_phrase(score):
    """Retorna uma frase baseada na pontuação."""
    if score >= 90:
        return "💖 ALMAS GÊMEAS! O destino está selado."
    elif score >= 70:
        return "💘 Forte conexão. Isso tem potencial!"
    elif score >= 50:
        return "✨ Uma boa combinação. Tentem sair!"
    elif score >= 30:
        return "💔 Amigos, talvez. Mas o amor é uma jornada difícil aqui."
    else:
        return "💀 Desastre. Mantenham distância."

def create_ship_bar(score):
    """Gera a barra de progresso visual."""
    filled_blocks = int(score / 10)
    empty_blocks = BAR_LENGTH - filled_blocks
    
    bar = (BAR_BLOCK * filled_blocks) + (EMPTY_BLOCK * empty_blocks)
    
    if score >= 80:
        emoji = "❤️‍🔥"
    elif score >= 40:
        emoji = "💞"
    else:
        emoji = "🥀"
        
    return f"`[{bar}]` {score}% {emoji}"

# ----------------------------------------------------
# 🚢 COMANDO !SHIP
# ----------------------------------------------------

@bot.command(name='ship', help='Calcula a compatibilidade entre dois membros. Ex: !ship @fulano @ciclano')
async def ship(ctx, member1: discord.Member, member2: discord.Member):
    # Garante que os membros são diferentes, a menos que seja um auto-ship
    if member1.id == member2.id:
        await ctx.send(f"❌ Você não pode calcular a compatibilidade de uma pessoa consigo mesma... mas se pudesse, seria 100%!")
        return

    # 1. Calcula a pontuação
    score = calculate_ship_score(member1.id, member2.id)
    
    # 2. Cria a visualização
    ship_bar = create_ship_bar(score)
    ship_phrase = get_ship_phrase(score)
    
    # 3. Cria o nome do "casal"
    # Pega os primeiros 4 caracteres do nome do membro 1 e os últimos 4 do nome do membro 2
    name1_part = member1.display_name[:4]
    name2_part = member2.display_name[-4:]
    ship_name = f'**{name1_part.capitalize()}{name2_part.capitalize()}**'
    
    embed = discord.Embed(
        title=f'🚢 Relatório de Compatibilidade: {ship_name}',
        description=f'O bot avaliou a conexão entre {member1.mention} e {member2.mention}.',
        color=discord.Color.red()
    )
    
    embed.add_field(name="Porcentagem de Conexão", value=ship_bar, inline=False)
    embed.add_field(name="Status do Relacionamento", value=ship_phrase, inline=False)
    
    embed.set_footer(text='Este resultado é totalmente científico e não pode ser questionado.')
    
    await ctx.send(embed=embed) 

    # --- CONFIGURAÇÃO DE MINERAÇÃO (MINING) ---
MINING_COOLDOWN = 900 # 15 minutos

MINING_ITEMS = {
    # Item: {Emoji, Preço, Peso (Chance)}
    "cobre": {"emoji": "🪙", "price": 50, "weight": 50},    # Mais comum
    "ferro": {"emoji": "🔩", "price": 150, "weight": 35},
    "ouro": {"emoji": "🥇", "price": 500, "weight": 10},
    "diamante": {"emoji": "💎", "price": 2500, "weight": 5} # Mais raro
}

# --- MAPA UNIFICADO PARA VENDA ---
# Junta itens da fazenda e mineração para facilitar a busca no !vd
ALL_SELLABLE_ITEMS = {
    **FARM_ITEMS, # Usa as chaves (trigo, alface, etc.) do FARM_ITEMS
    **MINING_ITEMS # Adiciona as chaves (cobre, ferro, etc.) do MINING_ITEMS
}
@bot.command(name='minerar', aliases=['mine'], help=f'Ganha minérios aleatórios. Cooldown de {MINING_COOLDOWN // 60} minutos.')
@commands.cooldown(1, MINING_COOLDOWN, commands.BucketType.user)
async def minerar(ctx):
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    inventory = user_data['farm']['inventory'] # Reutilizamos o inventário da fazenda
    
    # Define as chances de sorteio
    items = list(MINING_ITEMS.keys())
    weights = [MINING_ITEMS[item]['weight'] for item in items]
    
    # Sorteia de 3 a 6 itens por mineração
    num_drops = random.randint(3, 6) 
    drops = random.choices(items, weights=weights, k=num_drops)
    
    itens_minerados = {}
    
    for item_key in drops:
        item_info = MINING_ITEMS[item_key]
        item_full_name = f'{item_key.capitalize()} {item_info["emoji"]}'
        
        # Adiciona ao inventário
        inventory[item_full_name] = inventory.get(item_full_name, 0) + 1
        # Conta para o display de resultado
        itens_minerados[item_full_name] = itens_minerados.get(item_full_name, 0) + 1
        
    # Salva o inventário atualizado
    data = load_data()
    data[str(user_id)]['farm']['inventory'] = inventory
    save_data(data)
    
    # Cria o display dos itens minerados
    drops_display = '\n'.join([f'{count}x **{name}**' for name, count in itens_minerados.items()])
    
    embed = discord.Embed(
        title='⛏️ Mineração Concluída!',
        description='Você usou sua picareta e encontrou os seguintes recursos:',
        color=discord.Color.dark_red()
    )
    embed.add_field(name='Itens Encontrados', value=drops_display, inline=False)
    
    await ctx.send(embed=embed)

@minerar.error
async def minerar_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        tempo_restante = error.retry_after
        minutos = int(tempo_restante // 60)
        segundos = int(tempo_restante % 60)
        
        await ctx.send(f'⏳ Sua picareta precisa esfriar! Tempo restante: **{minutos}m {segundos}s**.', delete_after=10)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('❌ Formato inválido. Use apenas `!minerar`.')
# Deve estar aqui, sem espaços antes do @
@bot.command(name='vdmine', aliases=['vendermine'], help='Vende um item de mineração.')
async def vdmine(ctx, item_name: str = None, quantidade: int = 1):
    # ... código ...:
    user_id = ctx.author.id
    data = load_data()
    user_data = get_user_data(user_id)
    inventory = user_data['farm']['inventory']
    
    if quantidade <= 0:
        await ctx.send('❌ A quantidade a ser vendida deve ser positiva.')
        return
        
    # Limpa a chave do item (ex: 'trigo' de 'trigo 🌾')
    item_key_clean = item_name.lower().split()[0] if item_name else None
    
    # --- NOVO: Verifica no mapa unificado de itens vendáveis ---
    if item_key_clean not in ALL_SELLABLE_ITEMS:
        await ctx.send('❌ Item de fazenda ou minério inválido. Verifique a ortografia.')
        return

    item_info = ALL_SELLABLE_ITEMS[item_key_clean]
    
    # Recria o nome completo da chave do inventário (ex: 'Trigo 🌾' ou 'Cobre 🪙')
    item_full_name = f'{item_key_clean.capitalize()} {item_info["emoji"]}'
    
    # --- Lógica de Venda (Idêntica à anterior) ---
    
    if item_full_name not in inventory or inventory[item_full_name] < quantidade:
        estoque = inventory.get(item_full_name, 0)
        await ctx.send(f'❌ Você só tem **{estoque}** de {item_full_name} no inventário.')
        return
        
    preco_unitario = item_info['price']
    ganho_total = preco_unitario * quantidade
    
    inventory[item_full_name] -= quantidade
    if inventory[item_full_name] == 0:
        del inventory[item_full_name] 
        
    novo_saldo = update_user_balance(user_id, ganho_total)
    
    data[str(user_id)]['farm']['inventory'] = inventory
    save_data(data)

    embed = discord.Embed(
        title='💸 Venda Realizada!',
        description=f'Você vendeu **{quantidade}x {item_full_name}**.',
        color=discord.Color.teal()
    )
    embed.add_field(name='Ganho Total', value=f'**+{ganho_total:,} Moedas**', inline=True)
    embed.add_field(name='Novo Saldo', value=f'**{novo_saldo:,} Moedas**', inline=True)
    
    await ctx.send(embed=embed)
    user_id = ctx.author.id
    data = load_data()
    user_data = get_user_data(user_id)
    inventory = user_data['farm']['inventory']
    
    if quantidade <= 0:
        await ctx.send('❌ A quantidade a ser vendida deve ser positiva.')
        return
        
    # Limpa a chave do item (ex: 'trigo' de 'trigo 🌾')
    item_key_clean = item_name.lower().split()[0] if item_name else None
    
    # --- NOVO: Verifica no mapa unificado de itens vendáveis ---
    if item_key_clean not in ALL_SELLABLE_ITEMS:
        await ctx.send('❌ Item de fazenda ou minério inválido. Verifique a ortografia.')
        return

    item_info = ALL_SELLABLE_ITEMS[item_key_clean]
    
    # Recria o nome completo da chave do inventário (ex: 'Trigo 🌾' ou 'Cobre 🪙')
    item_full_name = f'{item_key_clean.capitalize()} {item_info["emoji"]}'
    
    # --- Lógica de Venda (Idêntica à anterior) ---
    
    if item_full_name not in inventory or inventory[item_full_name] < quantidade:
        estoque = inventory.get(item_full_name, 0)
        await ctx.send(f'❌ Você só tem **{estoque}** de {item_full_name} no inventário.')
        return
        
    preco_unitario = item_info['price']
    ganho_total = preco_unitario * quantidade
    
    inventory[item_full_name] -= quantidade
    if inventory[item_full_name] == 0:
        del inventory[item_full_name] 
        
    novo_saldo = update_user_balance(user_id, ganho_total)
    
    data[str(user_id)]['farm']['inventory'] = inventory
    save_data(data)

    embed = discord.Embed(
        title='💸 Venda Realizada!',
        description=f'Você vendeu **{quantidade}x {item_full_name}**.',
        color=discord.Color.teal()
    )
    embed.add_field(name='Ganho Total', value=f'**+{ganho_total:,} Moedas**', inline=True)
    embed.add_field(name='Novo Saldo', value=f'**{novo_saldo:,} Moedas**', inline=True)
    
    await ctx.send(embed=embed)
# --- RODAR O BOT ---

if __name__ == '__main__':
    # O seu token foi mantido aqui.
   
    try:
        bot.run('MTQzOTM3MjI4NjU2OTIyMjQyNg.GMUVf-.nSbDdy-zSJ_t3MpE6xyizpcgktY4C9jw4nDyV8') 
    except discord.LoginFailure:
        print("ERRO: Falha ao fazer login. Verifique se o token do bot está correto.")
    except Exception as e:
        print(f"Ocorreu um erro ao rodar o bot: {e}")
