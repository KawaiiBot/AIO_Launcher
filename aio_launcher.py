import json
import math
import os
import sys
import threading
import time

from data import Bot
from discord.ext.commands import when_mentioned_or as wmo
from discord.ext.commands import HelpFormatter
from utils import permissions


class HelpFormat(HelpFormatter):
    async def format_help_for(self, context, command_or_bot):
        """
        special help formatter that only
        adds an reaction to the command message.
        """
        if permissions.can_react(context):
            await context.message.add_reaction(chr(0x2705))

        return await super().format_help_for(context, command_or_bot)


class BotThread(threading.Thread):
    def __init__(self, client, instance_id):
        threading.Thread.__init__(self, target=self.run_client)
        self.id = instance_id
        self.client = client
        self.start()

    def execute(self, query):
        try:
            if query == "guilds.count":
                return len(self.client.guilds)
            elif query == "users.count":
                return len(self.client.users)
            elif query == "exit":
                self.client.loop.stop()
            else:
                return "invalid command"
        except Exception as e:
            return f"An error occurred while processing the query\n{e}"

    def run_client(self):
        self.client.run(token)

if __name__ == "__main__":
    shards_per_client = 20
    total_shards = 128

    with open("config.json") as f:
        data = json.load(f)
        token = data["token"]
        prefix = data["prefix"]

    bot = Bot(command_prefix=wmo(prefix), prefix=prefix,
              pm_help=True, help_attrs=dict(hidden=True),formatter=HelpFormat(), fetch_offline_members=False)

    for file in os.listdir("cogs"):
        if file.endswith(".py"):
            name = file[:-3]
            bot.load_extension(f"cogs.{name}")

    shards = []

    if "--sharded" in sys.argv:
        print("Sharding enabled. Validating shard count...")
        if total_shards >= 40 and total_shards % 16 != 0:  # 40 * 2,500 = 100,000 (see: https://github.com/discordapp/discord-api-docs/issues/387)
            print("Bad shard count: total_shards must be a multiple of 16")
            sys.exit(0)

        instances = math.ceil(total_shards / shards_per_client)
        bot.shard_count = total_shards

        for i in range(0, instances):
            start = i * shards_per_client
            last = start + shards_per_client

            if last > total_shards:
                last = total_shards

            print(f"[{i}] Creating bot instance (Shards {start}-{last})")
            ids = list(range(start, last))
    
            bot.shard_ids = ids

            shards.append(BotThread(bot, i))
    
    else:
        shards.append(BotThread(bot, 0))

    try:
        print("Waiting for all shards to emit READY")
        while not all(shard.client.is_ready() for shard in shards):
            time.sleep(1)

        while True:
            i = input(":: ")
            for shard in shards:
                print(f"[INSTANCE-{shard.id}]: {shard.execute(i)}")
            
            if i == "exit":
                sys.exit(0)
    except KeyboardInterrupt:
        for shard in shards:
            shard.client.loop.stop()
        sys.exit(0)
