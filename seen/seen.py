import asyncio
import contextlib
import datetime
import discord
import time
from typing import Union
from redbot.core import Config, commands
from redbot.core.i18n import Translator, cog_i18n

_SCHEMA_VERSION = 2
_ = Translator("Seen", __file__)


@cog_i18n(_)
class Seen(commands.Cog):
    """
    Shows last time a user was seen in chat.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=3870203059, force_registration=True
        )

        default_global = dict(schema_version=1)
        default_member = dict(seen=None)

        self.config.register_global(**default_global)
        self.config.register_member(**default_member)

        self._cache = {}
        self._task = self.bot.loop.create_task(self._save_to_config())

    @commands.guild_only()
    @commands.command(name="seen")
    @commands.bot_has_permissions(embed_links=True)
    async def _seen(self, ctx, author: discord.Member):
        """
        Shows last time a user was seen in chat.
        """
        member_seen_config = await self.config.member(author).seen()
        member_seen_cache = self._cache.get(author.guild.id, {}).get(author.id, None)

        if not member_seen_cache and not member_seen_config:
            embed = discord.Embed(
                colour=discord.Color.red(), title=_("I haven't seen that user yet.")
            )
            return await ctx.send(embed=embed)

        if not member_seen_cache:
            member_seen = member_seen_config
        elif not member_seen_config:
            member_seen = member_seen_cache
        elif member_seen_cache > member_seen_config:
            member_seen = member_seen_cache
        elif member_seen_config > member_seen_cache:
            member_seen = member_seen_config
        else:
            member_seen = member_seen_cache or member_seen_config

        now = int(time.time())
        time_elapsed = int(now - member_seen)
        output = self._dynamic_time(time_elapsed)

        if output[2] < 1:
            ts = _("just now")
        else:
            ts = ""
            if output[0] == 1:
                ts += _("{} day, ").format(output[0])
            elif output[0] > 1:
                ts += _("{} days, ").format(output[0])
            if output[1] == 1:
                ts += _("{} hour, ").format(output[1])
            elif output[1] > 1:
                ts += _("{} hours, ").format(output[1])
            if output[2] == 1:
                ts += _("{} minute ago").format(output[2])
            elif output[2] > 1:
                ts += _("{} minutes ago").format(output[2])
        em = discord.Embed(colour=discord.Color.green())
        avatar = author.avatar_url or author.default_avatar_url
        em.set_author(
            name=_("{} was seen {}").format(author.display_name, ts), icon_url=avatar
        )
        await ctx.send(embed=em)

    @staticmethod
    def _dynamic_time(time_elapsed):
        """
        Dynamic time calculation helper.
        """
        m, s = divmod(time_elapsed, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        return d, h, m

    def cog_unload(self):
        """
        Cleanup on unload.
        """
        self.bot.loop.create_task(self._clean_up())

    async def _clean_up(self):
        """
        Cleanup helper.
        """
        if self._task:
            self._task.cancel()
        if self._cache:
            group = self.config._get_base_group(
                self.config.MEMBER
            )  # Bulk update to config
            async with group.all() as new_data:
                for guild_id, member_data in self._cache.items():
                    if str(guild_id) not in new_data:
                        new_data[str(guild_id)] = {}
                    for member_id, seen in member_data.items():
                        new_data[str(guild_id)][str(member_id)] = {"seen": seen}

    async def _save_to_config(self):
        """
        Save helper.
        """
        await self.bot.wait_until_ready()
        with contextlib.suppress(asyncio.CancelledError):
            while True:
                users_data = self._cache.copy()
                self._cache = {}
                group = self.config._get_base_group(
                    self.config.MEMBER
                )  # Bulk update to config
                async with group.all() as new_data:
                    for guild_id, member_data in users_data.items():
                        if str(guild_id) not in new_data:
                            new_data[str(guild_id)] = {}
                        for member_id, seen in member_data.items():
                            new_data[str(guild_id)][str(member_id)] = {"seen": seen}

                await asyncio.sleep(60)

    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Message listener.
        """
        if getattr(message, "guild", None):
            if message.guild.id not in self._cache:
                self._cache[message.guild.id] = {}
            self._cache[message.guild.id][message.author.id] = int(time.time())

    @commands.Cog.listener()
    async def on_typing(
        self,
        channel: discord.abc.Messageable,
        user: Union[discord.User, discord.Member],
        when: datetime.datetime,
    ):
        """
        Typing listener.
        """
        if getattr(user, "guild", None):
            if user.guild.id not in self._cache:
                self._cache[user.guild.id] = {}
            self._cache[user.guild.id][user.id] = int(time.time())

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """
        Typing listener.
        """
        if getattr(after, "guild", None):
            if after.guild.id not in self._cache:
                self._cache[after.guild.id] = {}
            self._cache[after.guild.id][after.author.id] = int(time.time())

    @commands.Cog.listener()
    async def on_reaction_remove(
        self, reaction: discord.Reaction, user: Union[discord.Member, discord.User]
    ):
        """
        Remove listener.
        """
        if getattr(user, "guild", None):
            if user.guild.id not in self._cache:
                self._cache[user.guild.id] = {}
            self._cache[user.guild.id][user.id] = int(time.time())

    @commands.Cog.listener()
    async def on_reaction_add(
        self, reaction: discord.Reaction, user: Union[discord.Member, discord.User]
    ):
        """
        Reaction listener.
        """
        if getattr(user, "guild", None):
            if user.guild.id not in self._cache:
                self._cache[user.guild.id] = {}
            self._cache[user.guild.id][user.id] = int(time.time())
