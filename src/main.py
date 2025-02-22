import asyncio
from os import path
from typing import ClassVar, List, Mapping, Optional, Sequence

from typing_extensions import Self
from viam.components.sensor import Sensor
from viam.logging import getLogger
from viam.module.module import Module
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.services.discovery import Discovery
from viam.utils import ValueTypes, dict_to_struct

import BAC0
from BAC0.scripts.Lite import Lite

LOGGER = getLogger("lutron-bacnet:discover-devices")


class DiscoverDevices(Discovery, EasyResource):
    MODEL: ClassVar[Model] = Model(
        ModelFamily("hipsterbrown", "lutron-bacnet"), "discover-devices"
    )

    bacnet: Optional[Lite] = None

    @classmethod
    def new(
        cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ) -> Self:
        """This method creates a new instance of this Generic service.
        The default implementation sets the name from the `config` parameter and then calls `reconfigure`.

        Args:
            config (ComponentConfig): The configuration for this resource
            dependencies (Mapping[ResourceName, ResourceBase]): The dependencies (both implicit and explicit)

        Returns:
            Self: The resource
        """
        return super().new(config, dependencies)

    @classmethod
    def validate_config(cls, config: ComponentConfig) -> Sequence[str]:
        """This method allows you to validate the configuration object received from the machine,
        as well as to return any implicit dependencies based on that `config`.

        Args:
            config (ComponentConfig): The configuration for this resource

        Returns:
            Sequence[str]: A list of implicit dependencies
        """
        return []

    def reconfigure(
        self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ):
        """This method allows you to dynamically update your service when it receives a new `config` object.

        Args:
            config (ComponentConfig): The new configuration
            dependencies (Mapping[ResourceName, ResourceBase]): Any dependencies (both implicit and explicit)
        """
        device_json_file = path.abspath(
            path.join(path.dirname(__file__), "device.json")
        )
        self.bacnet = BAC0.start(json_file=device_json_file)
        return

    async def discover_resources(
        self,
        *,
        extra: Optional[Mapping[str, ValueTypes]] = None,
        timeout: Optional[float] = None,
    ) -> List[ComponentConfig]:
        LOGGER.info("Looking for resources")
        if self.bacnet is None:
            return []

        await self.bacnet._discover()
        devices = await self.bacnet._devices(_return_list=True)
        LOGGER.info(
            f"Discovered the following devices (count: {len(self.bacnet.discoveredDevices or {})})"
        )
        LOGGER.info(devices)

        configs: List[ComponentConfig] = []

        for deviceName, vendorName, devId, device_address, network_number in devices:
            try:
                objectList = await self.bacnet.read(
                    f"{device_address} device {devId} objectList"
                )
                LOGGER.info(f"{deviceName} object list: {objectList}")
                for obj_type, obj_address in objectList:
                    try:
                        if obj_type == "device":
                            continue

                        objectName = await self.bacnet.read(
                            f"{device_address} {obj_type} {obj_address} objectName"
                        )
                        presentValue = await self.bacnet.read(
                            f"{device_address} {obj_type} {obj_address} presentValue"
                        )
                        LOGGER.info(
                            f"Point for {deviceName}: {obj_type} {objectName} has value {presentValue}"
                        )
                    except Exception as readErr:
                        LOGGER.error(
                            f"Unable to get present value from {obj_type} at {obj_address}"
                        )
                        LOGGER.error(readErr)
            except Exception as err:
                LOGGER.error(f"Error reading {deviceName}: {err}")

            config = ComponentConfig(
                name=f"{deviceName} ({vendorName})",
                api=str(Sensor.API),
                model="hipsterbrown:lutron-bacnet:lutron-sensor",
                attributes=dict_to_struct(
                    {
                        "devId": devId,
                        "device_address": str(device_address),
                        "network_number": network_number.pop(),
                    }
                ),
            )
            configs.append(config)

        return configs

    async def do_command(
        self,
        command: Mapping[str, ValueTypes],
        *,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Mapping[str, ValueTypes]:
        raise NotImplementedError()

    async def close(self):
        if self.bacnet:
            await self.bacnet._disconnect()


if __name__ == "__main__":
    asyncio.run(Module.run_from_registry())
