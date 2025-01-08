import math
import os
import time
from tempfile import NamedTemporaryFile

import discord
from discord.utils import utcnow
from typing import List
from core import Cog, Context
from PIL import Image, ImageDraw, ImageFont
import hashlib
import random
from core import models


async def generate_wheel(names: List[str], winner_index: int) -> (discord.File, int):
    frames = []
    frame_duration = 100
    base_rotations = 4
    speed = 3
    total_rotation = 360 * base_rotations - (
            (360 / len(names)) * (winner_index + 0.5))  # todo the winner_index is not working proparly here
    spin_time = frame_duration
    for progress in range(0, 100 + speed, speed):
        rotation = int(await bezier_sample(progress / 100.0) * total_rotation)
        frames.append(await draw_frame(rotation, names))
        spin_time += frame_duration

    # export frames to gif
    frame_one = frames[0]
    with NamedTemporaryFile(prefix="utilitybelt_", suffix=".gif", delete=False) as temp_image:
        frame_one.save(temp_image, format="GIF", append_images=frames,
                       save_all=True, duration=frame_duration)
        temp_image.seek(0)
        return discord.File(fp=temp_image.name), spin_time


async def bezier_sample(t: float) -> float:  # todo should this ease more
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


class ButtonView(discord.ui.View):

    def __init__(self, cog: Cog, ctx: Context, names: List[str], winner: int,
                 members: List[discord.Member] = None) -> None:
        super().__init__()
        self.cog = cog
        self.ctx = ctx
        self.names = names
        self.members = members
        self.winner = winner

    @discord.ui.button(label="Re-spin", style=discord.ButtonStyle.primary)
    async def re_spin_callback(self, button: discord.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.ctx.edit(view=None, content=f"Spinning Wheel {self.cog.bot.get_emojis('loading_emoji')}")
        await WheelSpin.run(self.cog, self.ctx, self.names, self.members)

    @discord.ui.button(label="Spin Remaining", style=discord.ButtonStyle.primary)
    async def remaining_callback(self, button: discord.Button, interaction: discord.Interaction):
        # Do not spin if there is none left
        if len(self.names) <= 2:
            await interaction.respond(content="That was the final selection the wheel could make", ephemeral=True)
            return

        await interaction.response.defer()
        await self.ctx.edit(view=None, content=f"Spinning Wheel {self.cog.bot.get_emojis('loading_emoji')}")
        self.names.pop(self.winner)
        if self.members is not None:
            self.members.pop(self.winner)
        await WheelSpin.run(self.cog, self.ctx, self.names, self.members)


class WheelSpin(Cog):
    @discord.slash_command(
        integration_types={
            discord.IntegrationType.guild_install,
            discord.IntegrationType.user_install,
        },
        name="spin_wheel",
        description="Spins a wheel to choose a random user in your call"
    )
    async def spin_wheel_command(self, ctx: Context):
        active_voice = ctx.author.voice

        if active_voice is None:
            await ctx.respond(content="You need to be in a call to do this", ephemeral=True)

        active_channel = active_voice.channel
        members = active_channel.members
        names = []
        for member in members:
            if member.nick is None:
                names.append(member.global_name)
            else:
                names.append(member.nick)

        # if there is not enough members show error
        if len(members) <= 1:
            await ctx.respond(content="You need at least 2 people in your call to user this command", ephemeral=True)
            return

        # start the conversation
        await ctx.respond(content=f"Spinning Wheel {self.bot.get_emojis('loading_emoji')}")

        # tell the user the wheel is being spun
        await WheelSpin.run(self, ctx, names, members)

    async def run(self, ctx: Context, names: List[str], members: List[discord.Member] = None):
        # generate result of the wheel
        winner = random.randint(0, len(names) - 1)

        file, spin_time = await generate_wheel(names, winner)

        await ctx.edit(content="", file=file)
        # remove image
        os.remove(file.fp.name)

        # output winner once animation i does
        time.sleep(spin_time / 1000 + 1)  # + buffer to handle it loading the gif at different speeds
        if members is None:
            await ctx.edit(content=f"The winner is `{names[winner]}`",
                           view=ButtonView(self, ctx, names, winner)
                           )
        else:
            await ctx.edit(content=f"The winner is {members[winner].mention}",
                           view=ButtonView(self, ctx, names, winner, members)

                           )


def setup(bot):
    bot.add_cog(WheelSpin(bot))
