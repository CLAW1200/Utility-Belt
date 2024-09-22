from discord import DiscordException
from discord.ext import commands

from typing import Any, Literal
import io
import aiohttp
from PIL import Image, UnidentifiedImageError
from bs4 import BeautifulSoup as bs

import csv
import json
import os
import datetime
from datetime import timedelta
from core import models

__all__ = (
    "s",
    "list_items",
    "humanize_time",
    "image_to_gif",
    "Lowercase",
    "BotMissingPermissions",
    "image_or_url",
    "log_data_to_csv",
)

# functions
def s(data) -> Literal["", "s"]:
    if isinstance(data, str):# if data is a string
        data = int(not data.endswith("s")) # if the string ends with s, return 0, else return 1
    elif hasattr(data, "__len__"): # if data has a length 
        data = len(data) # get the length of the data
    check = data != 1 # if data is not equal to 1
    return "s" if check else "" # return s if check is true, else return an empty string


def list_items(items) -> str:
    return (
        f"{', '.join(items[:-1])} and {items[-1]}"
        if len(items) > 1
        else items[0]
    )

def humanize_time(time: timedelta) -> str:
    if time.days > 365:
        years, days = divmod(time.days, 365)
        return f"{years} year{s(years)} and {days} day{s(days)}"
    if time.days > 1:
        return f"{time.days} day{s(time.days)}, {humanize_time(timedelta(seconds=time.seconds))}"
    hours, seconds = divmod(time.seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if hours > 0:
        return f"{hours} hour{s(hours)} and {minutes} minute{s(minutes)}"
    if minutes > 0:
        return f"{minutes} minute{s(minutes)} and {seconds} second{s(seconds)}"
    return f"{seconds} second{s(seconds)}"

async def image_or_url(image, url):
    """Return an image from an attachment or URL, including GIFs"""
    async with aiohttp.ClientSession() as session:
        try:
            if image:
                async with session.get(image.url) as response:
                    response = await response.read()
                    return Image.open(io.BytesIO(response))
            if url:
                #Process a link to get the media link from a webpage
                async with session.get(url) as response:
                    response.raise_for_status()
                    #use beautifulsoup to get parsed html and find the meta tag with the image
                    try:
                        soup = bs(await response.text(), "html.parser")
                        meta = soup.find("meta", property="og:image")
                        if meta:
                            url = meta["content"]
                            async with session.get(url) as response:
                                response = await response.read()
                                return Image.open(io.BytesIO(response))
                        else:
                            return Image.open(io.BytesIO(await response.read()))
                    except UnicodeDecodeError:
                        return Image.open(io.BytesIO(await response.read()))
        except UnidentifiedImageError:
            raise ValueError("Invalid image")
        raise ValueError("No image or URL provided")

async def log_data(bot):
    # get stats
    date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    time = datetime.datetime.utcnow().strftime("%H:%M:%S")
    user_count = len(bot.users)
    guild_count = len(bot.guilds)
    guild_member_total = sum([guild.member_count for guild in bot.guilds])

    user_data_list = await models.UserModel.all()
    total_command_count = 0
    active_users = 0
    for user_data in user_data_list:
        total_command_count += user_data.commands_used or 0
        if user_data.commands_used:
            active_users += 1

    # write data to database
    await models.StatsModel.create(
        date=date,
        time=time,
        user_count=user_count,
        guild_count=guild_count,
        total_command_count=total_command_count,
        guild_member_total=guild_member_total,
        active_users=active_users
    )

# converters
class _Lowercase(commands.Converter):
    async def convert(self, ctx, text):
        return text.lower()

Lowercase: Any = _Lowercase()

# exceptions
class BotMissingPermissions(DiscordException):
    def __init__(self, permissions) -> None:
        missing = [
            f"**{perm.replace('_', ' ').replace('guild', 'server').title()}**"
            for perm in permissions
        ]
        sub = (
            f"{', '.join(missing[:-1])} and {missing[-1]}"
            if len(missing) > 1
            else missing[0]
        )
        super().__init__(f"I require {sub} permissions to run this command.")
