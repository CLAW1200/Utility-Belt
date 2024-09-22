from core import Cog, Context, utils
from discord.ext import tasks
import datetime

class LogStats(Cog):
    def __init__(self, bot):
        self.index = 0
        self.bot = bot
        self.printer.start()

    def cog_unload(self):
        self.printer.cancel()

    @tasks.loop(seconds=60)
    async def printer(self):
        now = datetime.datetime.now()
        # log data to csv every hour
        if now.minute == 0:
            await utils.log_data(self.bot)

    @printer.before_loop
    async def before_printer(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(LogStats(bot))