from logging import Logger, getLogger
from os import path
from threading import Lock
from typing import Self
import BAC0
from BAC0.scripts.Lite import Lite


class BacnetController:
    _instance = None
    _lock = Lock()
    _ref_count = 0
    client: Lite
    logger: Logger

    def __new__(cls) -> Self:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BacnetController, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, logger: Logger = getLogger("BacnetController")) -> None:
        with self._lock:
            if not self._initialized:
                self._initialized = True
                device_json_file = path.abspath(
                    path.join(path.dirname(__file__), "device.json")
                )
                self.client = BAC0.start(json_file=device_json_file)
                self.logger = logger
                self.logger.info("New controller created!")

            type(self)._ref_count += 1

    def release(self):
        with type(self)._lock:
            type(self)._ref_count -= 1
            if type(self)._ref_count <= 0 and type(self)._instance is not None:
                self.client.disconnect()
                type(self)._instance = None
                type(self)._ref_count = 0
