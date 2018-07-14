"""
:Module: device_manager.py

:Author:
    Peter Hyl

:Description: This module is used to obtain unique Unix system device file
              and loop device
"""
import logging
import os
import queue
import psutil
import shutil

from threading import Lock
from subprocess import CalledProcessError, TimeoutExpired, check_output


def singleton(cls):
    """
    Singleton
    """
    instances = {}
    lock = Lock()

    def _get_instance():
        """
        Get one instance of class
        """
        with lock:
            if cls not in instances:
                instances[cls] = cls()
            return instances[cls]

    return _get_instance


class ResourceQueue(queue.Queue):
    """
    Root class which represents resource queue for nbd, loop devices and mount points
    """

    def __init__(self, device):
        super().__init__()
        self.broken_queue = queue.Queue()
        self.all_devices = []
        self.init(device)

    def init(self, path):
        """
        Custom init which loads queue with devices
        """
        logging.info("Initializing ... %s", path)
        # I use nbd and loop device only 10-99
        for i in range(10, 100):
            device = path + str(i)
            if os.path.exists(device):
                super.put(device, block=True, timeout=None)
                self.all_devices.append(device)

    def get(self, block=True, timeout=None):
        """
        Returns first free device/mountpoint from queue
        """
        while True:
            dev = self.get_device(block=block, timeout=timeout)
            if self.is_available(dev):
                return dev
            self.broken_queue.put(dev, block, timeout)
            logging.error("Currently broken devices/mountpoints:\n %s", self.broken_queue.queue)

    def get_device(self, block, timeout):
        """
        Returns first device/mountpoint from queue
        """
        logging.debug("Queue before get: %s", self.queue)
        dev = super().get(block, timeout)
        logging.debug("Queue after get: %s", self.queue)
        return dev

    def put(self, item, block=True, timeout=None):
        """
        Releases device/mountpoints and returns it back to queue.
        If is not available/broken it is not returned, intead it is inserted into "broken" queue
        """
        logging.debug("Queue before put: %s", self.queue)
        if self.is_available(item):
            super().put(item, block, timeout)
            logging.debug("Queue after put: %s", self.queue)
        else:
            self.broken_queue.put(item)
            logging.error("Broken queue after put: %s", self.broken_queue.queue)

    # pylint: disable=no-self-use
    def is_available(self, device):
        """
        Check if device is available
        """
        func = "fuser"

        try:
            out = check_output([func, device])
            logging.warning("Device %s still in use: %s", device, out)
        except CalledProcessError:
            return True
        except TimeoutExpired as err:
            logging.debug("[%s] - Device: %s", err, device)
            return False
            # pylint: enable=no-self-use


@singleton
class NbdDevQueue(ResourceQueue):
    """
    This class represents NBD device class
    """

    def __init__(self):
        super().__init__("/dev/nbd")


@singleton
class LoopDevQueue(ResourceQueue):
    """
    This class represents LOOP device class
    """

    def __init__(self):
        super().__init__("/dev/loop")


@singleton
class MountQueue(ResourceQueue):
    """
    This class represents mount device class
    """

    def __init__(self):
        super().__init__("/mnt/device")

    def init(self, device_path):
        """
        Custom init
        """
        logging.info("Initializing ... %s", device_path)
        if os.path.exists(device_path):
            shutil.rmtree(device_path)

        for i in range(1, 256):
            device = os.path.join(device_path, str(i))

            # if directory does not exists, create it
            if not os.path.isdir(device):
                os.makedirs(device, exist_ok=True)

            # check if mountpoint is in used
            if not self.is_available(device):
                continue
            # add it to queue
            super().put(device)

    def is_available(self, mount):
        """
        Check if device is available
        """
        all_pids = psutil.pids()
        for pid in all_pids:
            try:
                process = psutil.Process(pid)
                process_name = process.name()
                process_cmd = process.cmdline()
            except psutil.NoSuchProcess:
                # This process does not exists anymore.
                # We can skip it.
                pass
            else:
                if mount in process_cmd:
                    logging.error("Mountpoint is used: %s\nProcess name:%s\nCmd line:%s",
                                  mount, process_name, process_cmd)
                    return False

        files = os.listdir(mount)
        count = len(files)
        if count > 1:
            logging.error("Mountpoint is used: %s\nFiles in dir:%s", mount, files)
            return False
        return True
