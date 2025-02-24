import asyncio
from viam.module.module import Module
import discovery as _discovery

if __name__ == "__main__":
    asyncio.run(Module.run_from_registry())
