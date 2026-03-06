import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import asyncio
import os
from dotenv import load_dotenv

# Charge les variables d'environnement
load_dotenv()
from datetime import datetime, time
from database import BirthdayDatabase

# Chargement de la configuration
# Chargement de la configuration
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
except FileNotFoundError:
    # Configuration par défaut si le fichier n'existe pas
    config = {
        "channel_name": "🍻-taverne",
        "check_time": "09:00"
    }

# Récupère le token depuis les variables d'environnement
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("❌ ERREUR : Token Discord non trouvé !")
    print("Crée un fichier .env avec : DISCORD_TOKEN=ton_token")
    exit()

# Configuration du bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
db = BirthdayDatabase()

# Dictionnaire des mois en français
MOIS = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}

@bot.event
async def on_ready():
    """Événement au démarrage du bot"""
    print(f'✅ Bot connecté en tant que {bot.user}')
    print(f'📊 Serveurs: {len(bot.guilds)}')
    
    # Initialisation de la base de données
    await db.init_db()
    print('✅ Base de données initialisée')
    
    # Synchronisation des commandes slash
    try:
        synced = await bot.tree.sync()
        print(f'✅ {len(synced)} commandes slash synchronisées')
    except Exception as e:
        print(f'❌ Erreur lors de la synchronisation: {e}')
    
    # Démarrage de la vérification quotidienne
    check_birthdays.start()
    print('✅ Vérification des anniversaires activée')

@tasks.loop(time=time(hour=int(config['check_time'].split(':')[0]), 
                      minute=int(config['check_time'].split(':')[1])))
async def check_birthdays():
    """Vérifie les anniversaires chaque jour"""
    now = datetime.now()
    birthdays = await db.get_today_birthdays(now.day, now.month)
    
    if not birthdays:
        return
    
    # Recherche du salon
    for guild in bot.guilds:
        channel = discord.utils.get(guild.text_channels, name=config['channel_name'])
        if channel:
            for user_id, username, day, month, year in birthdays:
                member = guild.get_member(user_id)
                
                # Calcul de l'âge si l'année est renseignée
                age_text = ""
                if year:
                    age = now.year - year
                    age_text = f" ({age} ans)"
                
                # Création de l'embed
                embed = discord.Embed(
                    title="🎉 JOYEUX ANNIVERSAIRE ! 🎂",
                    description=f"Aujourd'hui, c'est l'anniversaire de **{username}**{age_text} !",
                    color=discord.Color.gold()
                )
                embed.set_thumbnail(url=member.avatar.url if member and member.avatar else None)
                embed.add_field(name="🎈", value="Souhaitons-lui un excellent anniversaire !", inline=False)
                embed.set_footer(text=f"🎊 {day} {MOIS[month]}")
                
                await channel.send(
                    content=f"🎉 {member.mention if member else '@everyone'} 🎉",
                    embed=embed
                )
                print(f'🎂 Message d\'anniversaire envoyé pour {username}')

@bot.tree.command(name="anniversaire", description="Gestion des anniversaires")
@app_commands.describe(
    action="Action à effectuer",
    utilisateur="L'utilisateur concerné",
    jour="Jour de naissance (1-31)",
    mois="Mois de naissance (1-12)",
    annee="Année de naissance (optionnel)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="➕ Ajouter", value="ajouter"),
    app_commands.Choice(name="❌ Supprimer", value="supprimer"),
    app_commands.Choice(name="📋 Liste", value="liste"),
    app_commands.Choice(name="🔍 Voir", value="voir")
])
async def anniversaire(
    interaction: discord.Interaction,
    action: app_commands.Choice[str],
    utilisateur: discord.Member = None,
    jour: int = None,
    mois: int = None,
    annee: int = None
):
    """Commande principale de gestion des anniversaires"""
    
    if action.value == "ajouter":
        # Vérifications
        if not utilisateur or jour is None or mois is None:
            await interaction.response.send_message(
                "❌ Pour ajouter un anniversaire, vous devez spécifier: utilisateur, jour et mois",
                ephemeral=True
            )
            return
        
        if not (1 <= jour <= 31) or not (1 <= mois <= 12):
            await interaction.response.send_message(
                "❌ Date invalide ! Jour: 1-31, Mois: 1-12",
                ephemeral=True
            )
            return
        
        if annee and (annee < 1900 or annee > datetime.now().year):
            await interaction.response.send_message(
                "❌ Année invalide !",
                ephemeral=True
            )
            return
        
        # Ajout dans la base de données
        await db.add_birthday(
            utilisateur.id,
            utilisateur.display_name,
            jour,
            mois,
            annee,
            interaction.user.id
        )
        
        date_str = f"{jour} {MOIS[mois]}"
        if annee:
            date_str += f" {annee}"
        
        embed = discord.Embed(
            title="✅ Anniversaire ajouté !",
            description=f"L'anniversaire de **{utilisateur.display_name}** a été enregistré",
            color=discord.Color.green()
        )
        embed.add_field(name="📅 Date", value=date_str, inline=False)
        embed.set_thumbnail(url=utilisateur.avatar.url if utilisateur.avatar else None)
        
        await interaction.response.send_message(embed=embed)
    
    elif action.value == "supprimer":
        if not utilisateur:
            await interaction.response.send_message(
                "❌ Vous devez spécifier un utilisateur",
                ephemeral=True
            )
            return
        
        success = await db.remove_birthday(utilisateur.id)
        
        if success:
            embed = discord.Embed(
                title="✅ Anniversaire supprimé",
                description=f"L'anniversaire de **{utilisateur.display_name}** a été supprimé",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(
                f"❌ Aucun anniversaire trouvé pour {utilisateur.display_name}",
                ephemeral=True
            )
    
    elif action.value == "voir":
        if not utilisateur:
            await interaction.response.send_message(
                "❌ Vous devez spécifier un utilisateur",
                ephemeral=True
            )
            return
        
        birthday = await db.get_birthday(utilisateur.id)
        
        if birthday:
            user_id, username, day, month, year = birthday
            date_str = f"{day} {MOIS[month]}"
            
            embed = discord.Embed(
                title=f"🎂 Anniversaire de {username}",
                color=discord.Color.blue()
            )
            embed.add_field(name="📅 Date", value=date_str, inline=True)
            
            if year:
                age = datetime.now().year - year
                embed.add_field(name="🎈 Âge", value=f"{age} ans", inline=True)
            
            embed.set_thumbnail(url=utilisateur.avatar.url if utilisateur.avatar else None)
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(
                f"❌ Aucun anniversaire enregistré pour {utilisateur.display_name}",
                ephemeral=True
            )
    
    elif action.value == "liste":
        birthdays = await db.get_all_birthdays()
        
        if not birthdays:
            await interaction.response.send_message(
                "📋 Aucun anniversaire enregistré pour le moment",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🎂 Liste des anniversaires",
            description=f"Total: {len(birthdays)} anniversaire(s)",
            color=discord.Color.purple()
        )
        
        # Grouper par mois
        by_month = {}
        for user_id, username, day, month, year in birthdays:
            if month not in by_month:
                by_month[month] = []
            
            age_str = f" ({datetime.now().year - year} ans)" if year else ""
            by_month[month].append(f"• **{username}** - {day} {MOIS[month]}{age_str}")
        
        # Afficher par mois
        for month in sorted(by_month.keys()):
            embed.add_field(
                name=f"📅 {MOIS[month]}",
                value="\n".join(by_month[month]),
                inline=False
            )
        
        embed.set_footer(text=f"Demandé par {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="test_anniversaire", description="Teste le message d'anniversaire (Admin uniquement)")
@app_commands.checks.has_permissions(administrator=True)
async def test_anniversaire(interaction: discord.Interaction):
    """Commande de test pour les administrateurs"""
    channel = discord.utils.get(interaction.guild.text_channels, name=config['channel_name'])
    
    if not channel:
        await interaction.response.send_message(
            f"❌ Salon '{config['channel_name']}' introuvable",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="🎉 JOYEUX ANNIVERSAIRE ! 🎂",
        description=f"Aujourd'hui, c'est l'anniversaire de **{interaction.user.display_name}** !",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
    embed.add_field(name="🎈", value="Souhaitons-lui un excellent anniversaire !", inline=False)
    embed.set_footer(text="🧪 Ceci est un test")
    
    await channel.send(
        content=f"🎉 {interaction.user.mention} 🎉",
        embed=embed
    )
    
    await interaction.response.send_message("✅ Message de test envoyé !", ephemeral=True)

# Lancement du bot
if __name__ == "__main__":
    bot.run(TOKEN)
