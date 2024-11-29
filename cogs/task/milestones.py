from core import Cog
from discord.ext import tasks
import datetime
import discord
import asyncio

class Birthday(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.birthday.start()

    def cog_unload(self):
        self.birthday.cancel()

    @tasks.loop(hours=24)
    # get bot account creation date
    async def birthday(self):
        await asyncio.sleep(2) # avoid conflict with setting status when bot is starting
        bot = self.bot
        created_at = bot.user.created_at
        today = datetime.datetime.now()
        if created_at.day == today.day and created_at.month == today.month:
            await bot.change_presence(activity=discord.CustomActivity(name=f"{today.year - created_at.year} years of service! 🎉"))

    @birthday.before_loop
    async def before_birthday(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(Birthday(bot))
