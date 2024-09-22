import discord
import os
from core import Cog, Context, utils
from PIL import Image, ImageChops, UnidentifiedImageError
from tempfile import NamedTemporaryFile
import aiohttp
import re
import hashlib
from urllib.parse import unquote

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

    overlay = overlay.resize((image.width, int(image.height * overlay_y)))

    output = Image.new("RGBA", image.size)
    output.paste(overlay, (0, 0), overlay)

    frame = ImageChops.composite(output, image, output)
    frame = ImageChops.subtract(image, output)
    
    with NamedTemporaryFile(suffix=".gif", delete=False) as temp_image:
        frame.save(temp_image, format="GIF")
        temp_image.seek(0)
        return discord.File(fp=temp_image.name)
    
async def download_media(url, format, quality):
    """Download media from a URL"""
    api_url = "https://olly.imput.net/api/json"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
        }
    data = {
        "url": url,
        "filenamePattern": "pretty",
        "twitterGif": "true",
        "youtubeVideoCodec": "h264",
        "audioBitrate": "128",
        }
    
    if format == "auto":
        data["downloadMode"] = "auto"
        data["videoQuality"] = quality

    if format == "audio":
        data["downloadMode"] = "audio"
        data["audioFormat"] = quality

    if format == "mute":
        data["downloadMode"] = "mute"
        data["videoQuality"] = quality


    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, headers=headers, json=data) as response:
            if response.status != 200:
                response_json = await response.json()
                raise discord.errors.ApplicationCommandError(f"Invalid URL")
            response_json = await response.json()
            media_url = response_json.get("url")
        
        async with session.get(media_url) as media:
            media.raise_for_status()
            content_disposition = media.headers.get("content-disposition")
            if content_disposition:
                # Check for encoded filename (RFC 5987)
                match = re.search("filename\*=UTF-8''(.+)", content_disposition)
                if match:
                    # Decode the percent-encoded UTF-8 part and get file extension
                    filename = unquote(match.group(1))
                    file_ext = match.group(1).split(".")[-1]
                else:
                    # Fallback to regular expression if not encoded
                    match = re.search('filename=(.+)', content_disposition)
                    if match:
                        filename = match.group(1)

            else:
                filename = hashlib.sha256(url.encode()).hexdigest()
                file_ext = "mp4" # assume mp4 if no content-disposition
                filename = filename + "." + file_ext

            media = await media.read()

    with NamedTemporaryFile(delete=False) as temp_media:
        if filename[0] == '"':
            filename = filename[1:]
        temp_media.write(media)
        temp_media.seek(0)
        return discord.File(fp=temp_media.name, filename=filename)


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
    async def image_to_gif(self, ctx: Context, image: discord.Attachment = None, url: str = None):
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
        type=float,
        required=False,
        default=0.2
    )
    async def speech_bubble(self, ctx: Context, image: discord.Attachment = None, url: str = None, overlay_y: float = 0.5):
        """Add a speech bubble to an image using speech_bubble"""
        await ctx.respond(content = f"Adding speech bubble to image {self.bot.get_emojis('loading_emoji')}")
        if not image and not url:
            raise discord.errors.ApplicationCommandError("No image or URL provided")
        file = await speech_bubble(image, url, overlay_y)
        await ctx.edit(content = f"", file=file)
        os.remove(file.fp.name)

    async def get_quality_types(ctx: discord.AutocompleteContext):
        format = ctx.options["format"]
        if format == "audio":
            return ["best", "mp3", "wav", "opus", "ogg"]
        if format == "video":
            return ["best", "144", "240", "360", "480", "720", "1080", "1440", "2160"]
        
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
        "quality",
        description="The download quality",
        type=str,
        autocomplete=discord.utils.basic_autocomplete(get_quality_types), 
        required=False,
    )

    async def download_media(self, ctx: Context, url: str, format: str, quality: str):
        """Download media from a URL using download_media"""
        try:
            url_short = url.split('/')[2]
        except IndexError:
            url_short = url
        await ctx.respond(content = f"Downloading media from {url_short} {self.bot.get_emojis('loading_emoji')}")
        file = await download_media(url, format, quality) # discord file object
        await ctx.edit(content = f"", file=file)
        os.remove(str(file.fp.name))

def setup(bot):
    bot.add_cog(Media(bot))
