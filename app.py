import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Agora o 'config' pode ser importado, pois as variáveis já estão no ambiente
from config import config

class TemplateBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix=config.PREFIX, intents=intents)

    async def setup_hook(self):
        """Este hook é chamado automaticamente antes do bot logar."""
        print("--- Carregando funcionalidades (Cogs) ---")
        
        for extension, is_active in config.MODULOS_ATIVOS.items():
            if is_active:
                try:
                    await self.load_extension(extension)
                    print(f"✅ Módulo '{extension}' carregado com sucesso.")
                except Exception as e:
                    print(f"❌ Falha ao carregar o módulo '{extension}': {e}")
            else:
                print(f"⚪ Módulo '{extension}' desativado na configuração.")

        print("--- Sincronizando comandos de barra ---")
        # Sincroniza os comandos híbridos com o Discord
        await self.tree.sync()
        print("✅ Comandos de barra sincronizados.")
        print("-----------------------------------------")

    async def on_ready(self):
        print(f'--- Bot conectado como {self.user} ---')

async def main():
    bot = TemplateBot()
    # Verifica se o TOKEN foi carregado antes de iniciar
    if not config.TOKEN:
        print("❌ ERRO CRÍTICO: O token do Discord não foi encontrado.")
        print("Certifique-se de que o arquivo .env existe e contém a variável DISCORD_TOKEN.")
        return
    await bot.start(config.TOKEN)

if __name__ == "__main__":
    asyncio.run(main())