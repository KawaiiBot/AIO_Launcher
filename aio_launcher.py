import math
import sys
import asyncio
from multiprocessing import Process

import instance

if __name__ == "__main__":
    shards_per_instance = 2
    total_shards = 2

    shards = []

    if "--sharded" in sys.argv:
        print("Sharding enabled. Validating shard count...")
        if total_shards >= 40 and total_shards % 16 != 0:  # 40 * 2,500 = 100,000 (see: https://github.com/discordapp/discord-api-docs/issues/387)
            print("Bad shard count: total_shards must be a multiple of 16")
            sys.exit(0)

        instances = math.ceil(total_shards / shards_per_instance)
        print(f'Using {instances} instances')

        for i in range(0, instances):
            start = i * shards_per_instance
            last = start + shards_per_instance

            if last > total_shards:
                last = total_shards

            print(f"[{i}] Creating bot instance (Shards {start}-{last})")
            ids = list(range(start, last))

            p = Process(target=instance.Instance, args=(i, total_shards, ids,))
            shards.append(p)
            p.start()

    else:
        p = Process(target=instance.Instance, args=(0, 1, [0],))
        shards.append(p)
        p.start()

    loop = asyncio.get_event_loop()

    print('All instances launched.')

    async def waiter():
        await asyncio.sleep(5)

    while True:  # Keep the main process up
        loop.run_until_complete(waiter())
