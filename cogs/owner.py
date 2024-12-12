from discord.ext.commands import command
from jishaku.codeblocks import codeblock_converter
from jishaku.modules import ExtensionConverter
import discord
from core import Cog, models
from core import utils
import aiohttp
import subprocess
import os
import sys

class Owner(Cog, command_attrs={"hidden": True}):
    def __init__(self, bot) -> None:
        super().__init__(bot)
        self.jishaku = bot.get_cog("Jishaku")

    @command(name="eval")
    async def _eval(self, ctx, *, code):
        await self.jishaku.jsk_python(ctx, argument=codeblock_converter(code))

    @command(aliases=["reload"])
    async def load(self, ctx, *files: ExtensionConverter):
        await self.jishaku.jsk_load(ctx, *files)

    @command()
    async def unload(self, ctx, *files: ExtensionConverter):
        await self.jishaku.jsk_unload(ctx, *files)

    @command()
    async def shutdown(self, ctx):
        await ctx.send("Shutting down.")
        await self.bot.close()

    @command()
    async def restart(self, ctx):
        await ctx.send("Restarting.")
        os.execv(sys.executable, ['python'] + sys.argv)

    @command()
    async def pull(self, ctx, *to_load: ExtensionConverter):
        await self.jishaku.jsk_git(ctx, argument=codeblock_converter("pull"))
        await self.jishaku.jsk_load(ctx, *to_load)

    @command()
    # set bot status in the format of {presence_text}
    async def presence(self, ctx, *, presence_text: str):

        await models.BotModel.update_or_create(
            {"presence_text": presence_text}
        )
        await self.bot.change_presence(
            activity=discord.CustomActivity(
                name=presence_text
            )
        )
        await ctx.reply(f"Presence updated to `{presence_text}`")

    @command(aliases=["percent"])
    # the percentage of users who have used a bot command (check if commandsUsed exists for each user)
    async def command_percentage(self, ctx):
        user_data_list = await models.UserModel.all()
        active_users = 0
        for user_data in user_data_list:
            if user_data.commands_used:
                active_users += 1
        percentage = (active_users / len(user_data_list)) * 100
        await ctx.reply(f"{percentage:.2f}% of users have used a command.")

    @command()
    async def manlog(self, ctx):
        #manually call the log_data_to_csv function
        await utils.log_data(self.bot)
        await ctx.reply("Data logged to db.")

    async def cog_check(self, ctx):
        return ctx.author.id in self.bot.owner_ids
    
    @command()
    async def cobalt(self, ctx):
        # check cobalt status on port 9000
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:9000/") as response:
                if response.status == 200:
                    data = await response.json()
                    try:
                        cobalt = data['cobalt']
                    except KeyError:
                        await ctx.reply("Cobalt is offline.")
                        return
                    try:
                        version = cobalt['version']
                    except KeyError:
                        version = "Unknown"
                    await ctx.reply(f"Cobalt is running on version `{version}`")
                else:
                    await ctx.reply("Cobalt is offline.")

    @command()
    async def ytdlp(self, ctx):
        # pip upgrade yt-dlp package
        sys = subprocess.run(["python3", "-m", "pip", "install", "--upgrade", "yt-dlp"])
        if sys.returncode == 0:
            await ctx.reply("yt-dlp upgraded successfully.\nRestart the bot to apply changes.")
        else:
            await ctx.reply("yt-dlp upgrade failed.")

def setup(bot):
    bot.add_cog(Owner(bot))