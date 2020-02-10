import asyncio
import math
import shutil
from datetime import datetime
from multiprocessing import Pipe, Process, cpu_count
from multiprocessing.connection import Connection
from threading import Thread
from time import sleep

from instance import Instance

loop = asyncio.get_event_loop()
executable = str(shutil.which('python3.6') or shutil.which('py')).split('/')[-1]

###################################################
#                   INFORMATION                   #
###################################################
# :: op codes                                     #
#  status: A status update from the instance.     #
#          CONNECTED - All shards are connected.  #
#                                                 #
###################################################


def log(name, severity, message, *args):
    dt_format = '%H:%M:%S'
    current_time = datetime.now().strftime(dt_format)
    formatted = message.format(*args)
    full_message = f'[{current_time}] [{severity.upper()}] {name.title()}: {formatted}'
    print(full_message)


class Shard:
    def __init__(self, manager, instance_id: int):
        self._manager = manager
        self.instance_id: int = instance_id

        shard_start: int = instance_id * manager.shards_per_instance
        shard_finish: int = min(shard_start + manager.shards_per_instance, manager.total_shards)
        self.shard_ids: list = list(range(shard_start, shard_finish))

        p, c = Pipe()
        self._process: Process = Process(target=Instance,
                                         args=(self.instance_id, self._manager.total_shards, self.shard_ids, c,))
        self._pipeline_parent: Connection = p
        self._pipeline_child: Connection = c
        # The child pipeline is used exclusively by the child process.
        # We only store a reference so we can close it later.

        self.deployed = False
        log('shard', 'debug', 'Spawned shard with the following options: instance_id={}, shard_ids={}, ', self.instance_id, self.shard_ids)

    @property
    def is_alive(self):
        return self._process.is_alive

    def send(self, data: object):
        self._pipeline_parent.send(data)

    def receive(self, timeout: int = 5):
        if not self._pipeline_parent.poll(timeout):
            return None

        return self._pipeline_parent.recv()

    def start(self):
        if self.is_alive():
            self._process.kill()
            self.deployed = False

        self._process.start()
        self.deployed = True

    def shutdown(self):
        self._process.terminate()
        self._pipeline_parent.close()
        self._pipeline_child.close()


class Manager:
    def __init__(self, total_shards: int, max_instances: int = cpu_count()):
        self.total_shards: int = total_shards
        self.max_instances: int = max_instances
        self.shards_per_instance: int = math.ceil(total_shards / max_instances)

        self._monitor_thread = Thread(target=self.monitor_shards)
        self.shards = {}

    def deploy(self):
        if not self._monitor_thread.is_alive():
            self._monitor_thread.start()

        for i in range(self.max_instances):
            log('manager', 'info', 'Launching instance {}', i)
            self.spawn(i)
            resp = self.shards[i].receive(None)

            if resp is None:
                log('manager', 'warning', 'Expected a response from instance {} but received None!', i)
                continue

            if resp['op'] == 'status' and resp['d'] == 'CONNECTED':
                log('manager', 'info', 'Instance {} successfully deployed; all shards connected.', i)

    def spawn(self, shard_id: int):
        if shard_id in self.shards:
            self.shards[shard_id].shutdown()

        self.shards[shard_id] = Shard(self, shard_id)
        self.shards[shard_id].start()

    def monitor_shards(self):
        while True:
            for shard_id, shard in self.shards.items():
                if shard.deployed and not shard.is_alive:
                    log('manager', 'warning', 'Instance {} is marked as deployed, but the process is not alive. Restarting...', i)
                    self.spawn(shard_id)

            sleep(10)  # Check every 10 seconds.


if __name__ == '__main__':
    manager = Manager(10, 5)
    manager.deploy()
