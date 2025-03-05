import asyncio
from viam.module.module import Module
import discovery as _discovery
import sensor as _sensor
import switch as _switch

if __name__ == "__main__":
    asyncio.run(Module.run_from_registry())
