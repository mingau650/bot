from discord.ext import commands
import discord
import hashlib
import json
import os
import random
import time
import asyncio
import sys


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
    # Se user2_id for None, trata como divórcio: remove o cônjuge de ambos
    if user2_id is None:
        # Remove spouse do user1
        if user1_str in data:
            spouse = data[user1_str].get('spouse')
            data[user1_str]['spouse'] = None
            # Se havia um cônjuge, remove o vínculo do outro lado
            if spouse is not None:
                spouse_str = str(spouse)
                if spouse_str in data:
                    data[spouse_str]['spouse'] = None
        save_data(data)
        return

    # Caso padrão: registra casamento entre user1 e user2
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
... (file continues)
