import asyncio

from viam.module.module import Module

# Imported for their side effect: each module registers its model on import.
import button as _button  # noqa: F401
import discovery as _discovery  # noqa: F401
import sensor as _sensor  # noqa: F401
import switch as _switch  # noqa: F401

if __name__ == "__main__":
    asyncio.run(Module.run_from_registry())
