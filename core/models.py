from tortoise import fields
from tortoise.models import Model

__all__ = ("BotModel", "StatsModel", "UserModel")

"""
This module contains the models for the database.
This is how the data is stored and retrieved from the database.
"""

class BotModel(Model):
    # class to store the bot data such as presence, etc.
    id = fields.IntField(pk=True)  
    presence_text = fields.CharField(max_length=100)

    @classmethod
    async def get_bot_presence(cls) -> dict:
        # method to get the bot presence
        return {
            "presence": (bot_data := await cls.all().first()) and {
                "presence_text": bot_data.presence_text
            }
        }
    
    class Meta:
        # metadata for the model
        table = "bot"

class StatsModel(Model):
    # class to store the bot's stats
    id = fields.IntField(pk=True)
    date = fields.DateField()
    time = fields.TimeField()
    user_count = fields.IntField()
    guild_count = fields.IntField()
    total_command_count = fields.IntField()
    guild_member_total = fields.IntField()
    active_users = fields.IntField()

    @classmethod
    async def get_stats(cls) -> dict:
        # method to get the bot's stats
        return {
            "stats": [
                {
                    "date": stats.date,
                    "time": stats.time,
                    "user_count": stats.user_count,
                    "guild_count": stats.guild_count,
                    "total_command_count": stats.total_command_count,
                    "guild_member_total": stats.guild_member_total,
                    "active_users": stats.active_users
                }
                for stats in await cls.all()
            ]
        }
    
    class Meta:
        # metadata for the model
        table = "stats"

class UserModel(Model):
    # class to store the user's data
    id = fields.IntField(pk=True)
    user_id = fields.BigIntField()
    user_name = fields.CharField(max_length=70)
    user_discriminator = fields.CharField(max_length=4)
    notes = fields.JSONField()
    baned = fields.BooleanField(default=False)
    commands_used = fields.IntField(default=0)

    @classmethod
    async def get_user_data(cls, user_id: int) -> dict:
        # method to get the user's data
        return {
            "user": (user_data := await cls.filter(user_id=user_id).first()) and {
                "user_id": user_data.user_id,
                "user_name": user_data.user_name,
                "user_discriminator": user_data.user_discriminator,
                "notes": user_data.notes,
                "baned": user_data.baned,
                "commands_used": user_data.commands_used
            }
        }
    
    class Meta:
        # metadata for the model
        table = "user"

    