import math
import os
from tempfile import NamedTemporaryFile

import discord
from discord.utils import utcnow
from typing import List
from core import Cog, Context
from PIL import Image, ImageDraw, ImageFont
import hashlib
import random
from core import models


async def generate_wheel(names: List[str], winner_index: int) -> discord.File:
    frames = []
    base_rotations = 4
    speed = 3
    total_rotation = 360 * base_rotations - ((360 / len(names)) * (winner_index + 0.5)) # todo the winner_index is not working proparly here
    for progress in range(0, 100 + speed, speed):
        rotation = int(await bezier_sample(progress / 100.0) * total_rotation)
        frames.append(await draw_frame(rotation, names))

    # export frames to gif
    frame_one = frames[0]
    with NamedTemporaryFile(prefix="utilitybelt_", suffix=".gif", delete=False) as temp_image:
        frame_one.save(temp_image, format="GIF", append_images=frames,
                       save_all=True, duration=10)
        temp_image.seek(0)
        return discord.File(fp=temp_image.name)


async def bezier_sample(t: float) -> float: # todo should this ease more
    return t * t * (3 - 2 * t)


async def draw_frame(rotation: int, names: List[str]) -> Image:
    frame_size = 1000
    wheel_padding = 30
    text_size = 60
    section_angle = 360 / len(names)
    # create empty background
    image = Image.new("RGBA", (frame_size, frame_size))
    draw = ImageDraw.Draw(image)
    # draw each section
    for name in names:
        # draw section
        draw.pieslice([wheel_padding, wheel_padding, frame_size - wheel_padding, frame_size - wheel_padding], rotation,
                      rotation + section_angle, "Blue", "Black",
                      3)  # todo better color based on name
        # draw name
        x, y, width, height = ImageFont.load_default(size=text_size).getbbox(name)  # todo max name length
        name_image = Image.new("RGBA", (width, height))
        name_draw = ImageDraw.Draw(name_image)
        name_draw.text((0, 0), name, fill="black", font_size=text_size)
        text_angle = 360 - (rotation + (section_angle / 2))  # rotation anti-clockwise
        name_image = name_image.rotate(text_angle, expand=1)
        width, height = name_image.size
        # position from center
        # find offset for center of section
        r = ((frame_size / 2) - wheel_padding) / 4
        # convert from the polar form to cartesian to find where to place the text
        x_offset = int(r * math.cos(math.radians(text_angle)))
        y_offset = - int(r * math.sin(math.radians(text_angle)))
        # calculate how the text in the name image is offset
        name_offset_x = int((text_size / 2) * math.cos(math.radians(text_angle + 90)))
        name_offset_y = int((text_size / 2) * math.sin(math.radians(text_angle + 90)))
        center = int(frame_size / 2)
        if x_offset > 0 and y_offset > 0:  # bottom right
            image.paste(name_image, (center + x_offset - name_offset_x, center + y_offset - name_offset_y),
                        name_image)
        elif x_offset > 0:  # top right
            image.paste(name_image, (center + x_offset + name_offset_x, center + y_offset + name_offset_y - height),
                        name_image)
        elif y_offset > 0:  # bottom left
            image.paste(name_image, (center + x_offset + name_offset_x - width, center + y_offset + name_offset_y),
                        name_image)
        else:  # top left
            image.paste(name_image,
                        (center + x_offset - name_offset_x - width, center + y_offset - name_offset_y - height),
                        name_image)

        # increase the rotation for the next section
        rotation += section_angle

    # draw marker triangle
    draw.regular_polygon(((frame_size - wheel_padding, frame_size / 2), wheel_padding), 3, 90,
                         "black")

    return image


class WheelSpin(Cog):

    @discord.slash_command(
        integration_types={
            discord.IntegrationType.guild_install,
            discord.IntegrationType.user_install,
        },
        name="spin_wheel",
        description="Spins a wheel to choose a random from call"
    )
    async def download_media_command(self, ctx: Context):
        print(ctx.author.id)

        active_voice = ctx.author.voice
        """
        # if the user is not in a channel do nothing todo do somthing
        if active_voice is None:
            raise discord.errors.ApplicationCommandError("Not in channel")
        # tell the user the wheel is being spun
        
        active_channel = active_voice.channel

        print(f"the active channel is{active_channel}")
        print(f"the members of channel{active_channel.members}")
        """
        await ctx.respond(content=f"Spinning wheel {self.bot.get_emojis('loading_emoji')}")
        file = await generate_wheel(["no", "yess","noooo", "yesooo","noooooo", "yesooooooooooo","noooooooo", "yesooo"],0)

        await ctx.edit(content=f"", file=file)
        os.remove(file.fp.name)
        # todo add winner message after finished spinning


def setup(bot):
    bot.add_cog(WheelSpin(bot))
