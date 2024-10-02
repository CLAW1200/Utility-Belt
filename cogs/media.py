import discord
import os
from core import Cog, Context, utils
from PIL import Image, ImageChops
from tempfile import NamedTemporaryFile
import aiohttp
import json
from requests.structures import CaseInsensitiveDict

async def image_to_gif(image, url):
    """Convert an image from a URL to a gif and return it as a file path"""
    image = await utils.image_or_url(image, url)
    with NamedTemporaryFile(suffix=".gif", delete=False) as temp_gif:
        image.save(temp_gif, format="PNG", save_all=True, append_images=[image])
        temp_gif.seek(0)
        return discord.File(fp=temp_gif.name)

async def speech_bubble(image, url, overlay_y):
    """Add a speech bubble to an image"""
    overlay = "assets/speechbubble.png"
    overlay = Image.open(overlay).convert("RGBA")

    image = await utils.image_or_url(image, url)
    image = image.convert("RGBA")

    overlay = overlay.resize((image.width, int(image.height * (overlay_y / 10))))

    output = Image.new("RGBA", image.size)
    output.paste(overlay, (0, 0), overlay)

    frame = ImageChops.composite(output, image, output)
    frame = ImageChops.subtract(image, output)
    
    with NamedTemporaryFile(suffix=".gif", delete=False) as temp_image:
        frame.save(temp_image, format="GIF")
        temp_image.seek(0)
        return discord.File(fp=temp_image.name)
    
async def download_media(url, download_mode, video_quality, audio_format):
    """Download media from a URL"""

    api_url = "https://kityune.imput.net/"
    
    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/json"
    headers["Content-Type"] = "application/json"

    data = {
        "url": url,
        "filenameStyle": "pretty",
        "downloadMode" : str(download_mode),
        "twitterGif": True,
    }
    
    data = json.dumps(data)
    
    if format == "audio":
        data["audioFormat"] = audio_format

    if format == "auto":
        data["videoQuality"] = video_quality
        data["audioFormat"] = audio_format

    if format == "mute":
        data["videoQuality"] = video_quality

    print (headers)
    print (data)


    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, data=data, headers=headers) as response:
            if response.status != 200:
                raise response.raise_for_status()
            response_json = await response.json()
            media_url = response_json.get("url")
            media_filename = response_json.get("filename")
        
        async with session.get(media_url) as media:
            if media.status != 200:
                raise media.raise_for_status()
            media = await media.read()

    with NamedTemporaryFile(delete=False) as temp_media:
        if media_filename[0] == '"':
            media_filename = media_filename[1:]
        temp_media.write(media)
        temp_media.seek(0)
        return discord.File(fp=temp_media.name, filename=media_filename)


class Media(Cog):
    """Media Commands"""

    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        discord.IntegrationType.user_install,
        },
        name="image-to-gif",
        description="Convert an image to a gif"
    )
    @discord.option(
        "url",
        description="The URL of the image to convert",
        type=str,
        required=False
    )
    @discord.option(
        "image",
        description="The image to convert",
        type=discord.Attachment,
        required=False
    )
    async def image_to_gif_command(self, ctx: Context, image: discord.Attachment = None, url: str = None):
        """Convert an image to a gif using image_to_gif"""
        await ctx.respond(content = f"Converting image to gif {self.bot.get_emojis('loading_emoji')}")
        if not image and not url:
            raise discord.errors.ApplicationCommandError("No image or URL provided")
        file = await image_to_gif(image, url)
        await ctx.edit(content = f"", file=file)
        os.remove(file.fp.name)

    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        discord.IntegrationType.user_install,
        },
        name="speech-bubble",
        description="Add a speech bubble to an image"
    )

    @discord.option(
    "url",
    description="The URL of the image to add a speech bubble to",
    type=str,
    required=False
    )
    @discord.option(
        "image",
        description="The image to add a speech bubble to",
        type=discord.Attachment,
        required=False
    )
    @discord.option(
        "overlay_y",
        description="The height of the speech bubble overlay",
        type=int,
        required=False,
        default=2
    )
    async def speech_bubble_command(self, ctx: Context, image: discord.Attachment = None, url: str = None, overlay_y: int = 2):
        """Add a speech bubble to an image using speech_bubble"""
        await ctx.respond(content = f"Adding speech bubble to image {self.bot.get_emojis('loading_emoji')}")
        if not image and not url:
            raise discord.errors.ApplicationCommandError("No image or URL provided")
        if overlay_y <= 0 or overlay_y > 10:
            raise discord.errors.ApplicationCommandError("Overlay y must be between 0 and 10")
        file = await speech_bubble(image, url, overlay_y)
        await ctx.edit(content = f"", file=file)
        os.remove(file.fp.name)

    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        discord.IntegrationType.user_install,
        },
        name="download",
        description="Download media from a URL"
    )
    @discord.option(
        "url",
        description="The URL of the media to download",
        type=str,
        required=True,
    )   
    @discord.option(
        "format",
        description="The type of media to download",
        type=str,
        choices=["audio", "auto", "mute"],
        required=False,
        default="auto",
    )
    @discord.option(
        "video_quality",
        description="The download quality",
        type=str,
        choices=["best", "144", "240", "360", "480", "720", "1080", "1440", "2160"],
        default="240",
        required=False,
    )
    @discord.option(
        "audio_format",
        description="The audio format",
        type=str,
        choices=["best", "mp3", "wav", "opus", "ogg"],
        default="mp3",
        required=False,
    )

    async def download_media_command(self, ctx: Context, url: str, format: str, video_quality: str, audio_format: str):
        """Download media from a URL using download_media"""
        try:
            url_short = url.split('/')[2]
        except IndexError:
            url_short = url
        await ctx.respond(content = f"Downloading media from {url_short} {self.bot.get_emojis('loading_emoji')}")
        file = await download_media(url, format, video_quality, audio_format)
        await ctx.edit(content = f"", file=file)
        os.remove(str(file.fp.name))

def setup(bot):
    bot.add_cog(Media(bot))
