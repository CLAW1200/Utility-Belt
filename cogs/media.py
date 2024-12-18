import discord
import os
import asyncio
from functools import partial
import yt_dlp.version
from core import Cog, Context, utils
from PIL import Image, ImageChops
from tempfile import NamedTemporaryFile
import aiohttp
import datetime
import yt_dlp

async def image_to_gif(image, url):
    """Convert an image from a URL to a gif and return it as a file path"""
    image = await utils.image_or_url(image, url)
    with NamedTemporaryFile(prefix="utilitybelt_", suffix=".gif", delete=False) as temp_gif:
        image.save(temp_gif, format="PNG", save_all=True, append_images=[image])
        temp_gif.seek(0)
        return discord.File(fp=temp_gif.name)
    
async def get_user_avatar(user: discord.User):
    """Get a user's avatar"""
    user_avatar = user.avatar
    # resize to 256x256
    user_avatar = user_avatar.with_size(256)
    return user_avatar


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
        frame.save(temp_image, format="PNG")
        temp_image.seek(0)
        return discord.File(fp=temp_image.name)


async def download_media_ytdlp(url, download_mode, video_quality, audio_format):
    # Configure yt-dlp options

    ytdl_options = {
        "format": "best",
        "outtmpl": "temp/%(uploader)s - %(title)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "noprogress": True,
        "nocheckcertificate": True,
        "cookiefile": ".cookies",
        "color": "never",
        "trim_file_name": True,
    }

    # default options
    if video_quality == "auto":
        video_quality = "360"
    if audio_format == "auto":
        audio_format = "mp3"

    if download_mode == "audio":
        ytdl_options["format"] = f"""
        bestaudio[ext={audio_format}]/
        bestaudio[acodec=aac]/
        bestaudio/
        best
        """

    if download_mode == "auto":
        ytdl_options["format"] = f"""
        bestvideo[vcodec=h264][height<={video_quality}]+bestaudio[acodec=aac]/
        bestvideo[vcodec=h264][height<={video_quality}]+bestaudio/
        bestvideo[vcodec=vp9][ext=webm][height<={video_quality}]+bestaudio[ext=webm]/
        bestvideo[vcodec=vp9][ext=webm][height<={video_quality}]+bestaudio/
        bestvideo[height<={video_quality}]+bestaudio/
        bestvideo+bestaudio/
        best
        """

    ytdl = yt_dlp.YoutubeDL(ytdl_options)

    # Run blocking operations in thread pool
    loop = asyncio.get_event_loop()
    try:
        info = await loop.run_in_executor(
            None,
            partial(ytdl.extract_info, url, download=True),
        )

        # print available codecs
        # for format in info["formats"]:
        #     format_id = format.get("format_id", "N/A")
        #     ext = format.get("ext", "N/A") 
        #     height = format.get("height", "N/A")
        #     vcodec = format.get("vcodec", "N/A")
        #     acodec = format.get("acodec", "N/A")
        #     format_note = format.get("format_note", "N/A")
        #     print(format_id, ext, height, vcodec, format_note, acodec)

    except yt_dlp.DownloadError as e:
        raise discord.errors.ApplicationCommandError(f"Error: {e}")
    except yt_dlp.ExtractorError as e:
        raise discord.errors.ApplicationCommandError(f"Error: {e}")


    filepath = ytdl.prepare_filename(info)

    # # Get the filepath after post-processing
    # if download_mode == "audio":
    #     # For audio, extension will be changed to the requested format
    #     filepath = ytdl.prepare_filename(info).rsplit(".", 1)[0] + f".{audio_format}"
    # else:
    #     # For video, extension will be mp4
    #     filepath = ytdl.prepare_filename(info).rsplit(".", 1)[0] + ".mp4"

    return discord.File(fp=filepath)
  
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
    async def speech_bubble_command(self, ctx: Context, image: discord.Attachment = None, url: str = None, user: discord.User = None, overlay_y: int = 2):
        """Add a speech bubble to an image using speech_bubble"""
        await ctx.respond(content = f"Adding speech bubble to image {self.bot.get_emojis('loading_emoji')}")
        if not image and not url and not user:
            raise discord.errors.ApplicationCommandError("No image or URL provided")
        if user != None:
            image = await get_user_avatar(user)
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
        choices=["auto", "audio"],
        required=False,
        default="auto",
    )
    @discord.option(
        "video_quality",
        description="The download quality",
        type=str,
        choices=["auto", "144", "240", "360", "480", "720", "1080"],
        default="auto",
        required=False,
    )
    @discord.option(
        "audio_format",
        description="The audio format",
        type=str,
        choices=["auto", "mp3", "wav", "opus", "ogg"],
        default="auto",
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
