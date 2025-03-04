from os import path
from threading import Lock
from typing import Self
import weakref
import BAC0
from BAC0.scripts.Lite import Lite


class BacnetController:
    _instance = None
    _lock = Lock()
    _ref_count = 0
    _refs = set()
    client: Lite

    def __new__(cls) -> Self:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BacnetController, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        with self._lock:
            if not self._initialized:
                self._initialized = True
                device_json_file = path.abspath(
                    path.join(path.dirname(__file__), "device.json")
                )
                self.client = BAC0.start(json_file=device_json_file)

            type(self)._ref_count += 1
            ref = weakref.ref(self, self._cleanup)
            type(self)._refs.add(ref)

    @classmethod
    def _cleanup(cls, ref):
        with cls._lock:
            if ref in cls._refs:
                cls._refs.remove(ref)
                cls._ref_count -= 1

                if cls._ref_count == 0 and cls._instance:
                    cls._instance.client.disconnect()
                    cls._instance = None

    def __del__(self):
        with type(self)._lock:
            type(self)._ref_count -= 1
            if type(self)._ref_count <= 0:
                self.client.disconnect()
