import json
import os
from datetime import datetime

import discord
from discord.ext.commands import AutoShardedBot
from discord.ext.commands import when_mentioned_or as wmo


class Instance:
    def __init__(self, instance, shard_count, ids, pipe):
        self.pipe = pipe
        self._shard_ids = list(ids)
        self._deployed = False

        with open('config.json') as r:
            config = json.load(r)

        self.bot = AutoShardedBot(command_prefix=wmo(config.get('prefix')), shard_count=shard_count, shard_ids=ids,
                                  help_attrs=dict(Hidden=True), pm_help=True, fetch_offline_members=False)

        self.bot.prefix = config.get('prefix')
        self.bot.instance = instance
        self.bot.startup = datetime.now()

        self.bot.add_listener(self.on_ready)
        self.bot.add_listener(self.on_shard_ready)
        self.bot.run(config.get('token'))

    async def on_shard_ready(self, shard_id):
        print('Shard id {} logged in.'.format(shard_id))

    async def on_ready(self):
        for file in os.listdir("cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                self.bot.load_extension(f"cogs.{name}")

        if self._shard_ids == list(self.bot.shards.keys()):
            self._deployed = True
            self.pipe.send({'op': 'status', 'd': 'CONNECTED'})

    async def on_message(self, msg):
        if not self.bot.is_ready() or msg.author.bot or \
                not (isinstance(msg.channel, discord.DMChannel) or msg.channel.permissions_for(msg.guild.me).send_messages):
            return

        await self.bot.process_commands(msg)
