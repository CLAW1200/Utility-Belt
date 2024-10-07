import discord
from discord.utils import utcnow
from core import Cog, Context
import hashlib
import random
from core import models

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
        
    async def get_leaderboard_stats(self):
        user_data_list = await models.UserModel.get_top_users()
        return user_data_list
    
    
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
        discord.IntegrationType.user_install,
        },
        name="leaderboard",
        description="Get the leaderboard"
    )
    
    async def leaderboard_command(self, ctx: Context):
        """Get the leaderboard"""
        await ctx.defer()
        user_data_list = await self.get_leaderboard_stats()
        embed = discord.Embed(title="Leaderboard", color=discord.Color.green())
        rank = 0
        for user_dict in user_data_list:
            if rank > 4:
                break
            # for the 1st place, set the image to the user's avatar on the side
            user = await self.bot.get_or_fetch_user(user_dict["user_id"]) # get the user object
            if user == None or user.bot or (user.id in self.bot.owner_ids):
                continue
            if rank == 0:
                embed.set_thumbnail(url = user.avatar.url)
            embed.add_field(name=f"#{rank + 1} {user.global_name}", value=f"Commands used: {user_dict['commands_used']}", inline=False)
            rank = rank + 1

        embed.set_footer(text=f"Stats as of {utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Misc(bot))
