import discord
from discord import app_commands
import ollama
from ollama import AsyncClient
from collections import defaultdict
import re
import os

def load_env_file():
    try:
        with open(".env", "r") as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        raise ValueError(".env file not found")
    except Exception as e:
        raise ValueError(f"Error reading .env file: {str(e)}")

load_env_file()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

conversation_history = defaultdict(list)
active_channels = set()

NOME = "concord"
MODEL = "gemma3:4b-it-qat"
SYSTEM = f"Você é um bot de Discord chamado {NOME}. Você gosta de conversar, você fala de forma concisa."

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    await tree.sync()
    print("Bot is ready!")

@tree.command(name="hi", description="Start a conversation with the bot")
async def hi(interaction: discord.Interaction):
    channel = interaction.channel
    if channel.id in active_channels:
        await interaction.response.send_message("**WARNING:** The bot is already running")
        return
    active_channels.add(channel.id)
    conversation_history[channel.id] = [{"role": "system", "content": SYSTEM}]
    await interaction.response.send_message("**ONLINE**")

@tree.command(name="bye", description="End the conversation with the bot")
async def bye(interaction: discord.Interaction):
    channel = interaction.channel
    if channel.id not in active_channels:
        await interaction.response.send_message("**WARNING:** There is no conversation in this channel")
        return
    active_channels.remove(channel.id)
    conversation_history[channel.id] = []
    await interaction.response.send_message("**OFFLINE**")

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return
    if message.channel.id in active_channels and not message.content.startswith("/"):
        async with message.channel.typing():
            try:
                history = conversation_history[message.channel.id]
                history.append({"role": "user", "content": message.content})
                response = await AsyncClient().chat(
                    model=MODEL,
                    messages=history,
                )
                ai_response = response["message"]["content"]
                ai_response = re.sub(r'<think>.*?</think>', '', ai_response, flags=re.DOTALL)
                ai_response = ai_response.replace('<think>', '').replace('</think>', '').strip()
                history.append({"role": "assistant", "content": ai_response})
                if len(history) > 10:
                    history = [history[0]] + history[-9:]
                conversation_history[message.channel.id] = history
                if len(ai_response) > 2000:
                    ai_response = ai_response[:1997] + "..."
                await message.channel.send(ai_response)
            except Exception as e:
                await message.channel.send(f"**ERROR:** {str(e)}")
                print(f"ERR: {e}")

TOKEN = os.environ.get("BOT_TOKEN")
client.run(TOKEN)