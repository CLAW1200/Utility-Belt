import discord
from discord.utils import utcnow
from core import Cog, Context
import hashlib
import random

class Misc(Cog):
    """Miscellaneous commands"""

    def peepee(self, user: discord.User):
        peepeeSize = int(hashlib.sha256(str(user.id).encode()).hexdigest(), 16) % 20 # get a random number between 0 and 19
        peepee = "8" + "=" * peepeeSize + "D"
        return peepee

    def get_random_user(self, ctx: Context):
        random_user = random.choice(self.bot.users)
        if random_user == ctx.author or random_user.bot:
            return self.get_random_user(ctx)
        else:
            return random_user
        
    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        },
        name="peepee",
        description="Get the size of your peepee"
    )
    @discord.option(
        "user",
        description="The user to get the peepee size of",
        type=discord.User,
        required=False
    )
    async def peepee_command(self, ctx: Context, user: discord.User):
        """Get the size of your peepee"""
        await ctx.defer()
        if user == None:
            user = ctx.author
        await ctx.respond(content = f"{user.mention} has a size of {self.peepee(user)}")

    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        },
        name="find-a-friend",
        description="Find a friend"
    )
    async def find_a_friend_command(self, ctx: Context):
        """Find a friend"""
        await ctx.defer()
        await ctx.respond(content = f"Your friend is {self.get_random_user(ctx).mention}")

def setup(bot):
    bot.add_cog(Misc(bot))
