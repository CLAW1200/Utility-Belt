import discord
import os
import asyncio
from functools import partial
import yt_dlp.version
from core import Cog, Context, utils
from PIL import Image, ImageChops
from tempfile import NamedTemporaryFile
import aiohttp
import json
from requests.structures import CaseInsensitiveDict
import datetime
import yarl
import yt_dlp

async def image_to_gif(image, url):
    """Convert an image from a URL to a gif and return it as a file path"""
    image = await utils.image_or_url(image, url)
    with NamedTemporaryFile(prefix="utilitybelt_", suffix=".gif", delete=False) as temp_gif:
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
    
    with NamedTemporaryFile(prefix="utilitybelt_",  suffix=".gif", delete=False) as temp_image:
        frame.save(temp_image, format="GIF")
        temp_image.seek(0)
        return discord.File(fp=temp_image.name)


async def download_media_ytdlp(url, download_mode, video_quality, audio_format):
    # Configure yt-dlp options
    print(video_quality)

    ytdl_options = {
        "format": "best",
        "outtmpl": "%(uploader)s - %(title)s.%(ext)s",
        "quiet": False,
        "no_warnings": False,
        "noplaylist": True,
        "nocheckcertificate": True,
        "cookiefile": "youtube.cookies",
    }

    if download_mode == "auto":
        if video_quality != "auto":
            ytdl_options["format"] = f"bestvideo[height<={video_quality}]+bestaudio/best[height<={video_quality}]"
        else:
            ytdl_options["format"] = f"bestvideo+bestaudio/best"
        ytdl_options["postprocessors"] = [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4"
        }]
    elif download_mode == "audio":
        ytdl_options["format"] = f"bestaudio/best"
        ytdl_options["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": audio_format,
            "preferredquality": "320"
        }]
    elif download_mode == "mute":
        ytdl_options["format"] = f"bestvideo[height<={video_quality}]"
        ytdl_options["postprocessors"] = [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4"
        }]

    ytdl = yt_dlp.YoutubeDL(ytdl_options)

    # Run blocking operations in thread pool
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(
        None, 
        partial(ytdl.extract_info, url, download=True)
    )
    
    # Get the filepath after post-processing
    if download_mode == "audio":
        # For audio, extension will be changed to the requested format
        filepath = ytdl.prepare_filename(info).rsplit(".", 1)[0] + f".{audio_format}"
    else:
        # For video, extension will be mp4
        filepath = ytdl.prepare_filename(info).rsplit(".", 1)[0] + ".mp4"

    return discord.File(fp=filepath)

async def download_media(url, download_mode, video_quality, audio_format):
    """Download media from a URL
        DEPRECATED!!
    """

    api_url = "http://localhost:9000/"
    
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
    
    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, data=data, headers=headers) as response:
            if response.status == 400:
                cobalt_error_code = json.loads(await response.text())["error"]["code"]
                raise discord.errors.ApplicationCommandError(f"## IMPORTANT: If you are having issues with YouTube, please read [this post](https://discord.gg/SpBUGEzmn8)\n{cobalt_error_code}\nCheck if the URL is valid and if the site is supported.\n")
            elif response.status == 429:
                cobalt_error_code = json.loads(await response.text())["error"]["code"]
                raise discord.errors.ApplicationCommandError(f"Too many requests.\nTry again later.\n{cobalt_error_code}")
            elif response.status != 200:
                response.raise_for_status()
            response_json = await response.json()
            media_url = response_json.get("url")
            media_filename = response_json.get("filename")
            media_url = yarl.URL(media_url, encoded=True)
    
        async with session.get(media_url, headers=headers) as media:
            if media.status != 200:
                raise media.raise_for_status()
            media_content = await media.read()
    
    with NamedTemporaryFile(delete=False, prefix="utilitybelt_") as temp_media:
        if media_filename[0] == '"':
            media_filename = media_filename[1:]
        temp_media.write(media_content)
        temp_media.seek(0)
        return discord.File(fp=temp_media.name, filename=media_filename)
    
async def upload_to_catbox(file): # pass a discord.File object
    """Upload media to catbox.moe with curl and return the URL"""
    file_raw = open(file.fp.name, "rb")
    file_type = file.filename.split(".")[-1]
    data = aiohttp.FormData()
    data.add_field("reqtype", "fileupload")
    data.add_field("time", "72h")
    data.add_field("fileToUpload", file_raw, filename="file.{}".format(file_type))
    async with aiohttp.ClientSession() as session:
        async def post(data) -> str:
            async with session.post("https://litterbox.catbox.moe/resources/internals/api.php", data=data) as response:
                text = await response.text()
                if not response.ok:
                    return None
                return text
        return await post(data)

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
        choices=["auto", "144", "240", "360", "480", "720", "1080", "1440", "2160"],
        default="auto",
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
        await ctx.defer()
        try:
            url_short = url.split('/')[2]
        except IndexError:
            url_short = url
        await ctx.respond(content = f"Downloading media from {url_short} {self.bot.get_emojis('loading_emoji')}")
        file = await download_media_ytdlp(url, format, video_quality, audio_format)
        try:
            await ctx.edit(content = f"", file=file)
        except discord.errors.HTTPException:
            await ctx.edit(content = f"Media is too big for discord, uploading to litterbox.catbox.moe instead {self.bot.get_emojis('loading_emoji')}")
            catbox_link = await upload_to_catbox(file)
            # get timestamp of 3 days from now in unix timestamp
            
            timestamp = datetime.datetime.now() + datetime.timedelta(days=3)
            timestamp = int(timestamp.timestamp())
            timestamp = str(f"<t:{timestamp}:R>")
            if catbox_link is not None:
                await ctx.edit(content = f"Expiry: {timestamp} {catbox_link}")
            else:
                await ctx.edit(content = f"Failed to upload to catbox.moe (file is probably still too big)")
        os.remove(str(file.fp.name))

def setup(bot):
    bot.add_cog(Media(bot))
