from core import Cog
from discord.ext import tasks
import datetime
import os
import shutil

class CleanTemp(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cleaner.start()

    def cog_unload(self):
        self.cleaner.cancel()
    
    @tasks.loop(seconds=(300))
    async def cleaner(self):
        now = datetime.datetime.now()
        # if a file or directory in temp/ is older than 5 minutes, delete it
        for file in os.listdir("temp/"):
            file_path = os.path.join("temp/", file)
            file_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            if (now - file_time).seconds > 300:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
        print (f"Cleaned temp/ directory at {now}")

    @cleaner.before_loop
    async def before_cleaner(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(CleanTemp(bot))