import asyncio
from typing import ClassVar, List, Mapping, Optional, Sequence

from typing_extensions import Self
from viam.components.sensor import Sensor
from viam.logging import getLogger
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.services.discovery import Discovery
from viam.utils import ValueTypes, dict_to_struct, struct_to_dict

from controller import BacnetController

LOGGER = getLogger("lutron-bacnet:discover-devices")


class DiscoverDevices(Discovery, EasyResource):
    MODEL: ClassVar[Model] = Model(
        ModelFamily("hipsterbrown", "lutron-bacnet"), "discover-devices"
    )

    bacnet: BacnetController

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
        attrs = struct_to_dict(config.attributes)
        self.max_query_concurrency = int(attrs.get("max_query_concurrency", 20))
        self.semaphore = asyncio.Semaphore(self.max_query_concurrency)
        self.bacnet = BacnetController()
        return

    async def discover_resources(
        self,
        *,
        extra: Optional[Mapping[str, ValueTypes]] = None,
        timeout: Optional[float] = None,
    ) -> List[ComponentConfig]:
        LOGGER.debug("Looking for resources")
        if self.bacnet is None:
            return []

        await self.bacnet.client._discover()
        devices = await self.bacnet.client._devices(_return_list=True)
        LOGGER.debug(
            f"Discovered the following devices (count: {len(self.bacnet.client.discoveredDevices or {})})"
        )
        LOGGER.debug(devices)

        configs: List[ComponentConfig] = []

        async def queryObjectDetails(deviceAddress, deviceObject):
            obj_type, obj_address = deviceObject
            baseQuery = f"{deviceAddress} {obj_type} {obj_address}"
            try:
                async with self.semaphore:
                    objectName = await self.bacnet.client.read(
                        f"{baseQuery} objectName"
                    )
                    return {
                        "name": str(objectName),
                        "address": str(obj_address),
                        "type": str(obj_type),
                    }
            except Exception as readErr:
                LOGGER.error(
                    f"Unable to get object name from {obj_type} at {obj_address}"
                )
                LOGGER.error(readErr)
                return {
                    "type": str(obj_type),
                    "address": str(obj_address),
                }

        async def queryDeviceObjects(device):
            deviceName, vendorName, devId, device_address, _network_number = device
            objects = []
            try:
                objectList = await self.bacnet.client.read(
                    f"{device_address} device {devId} objectList"
                )
                if objectList is not None:
                    objects = await asyncio.gather(*[
                        queryObjectDetails(device_address, deviceObject)
                        for deviceObject in objectList
                        if str(deviceObject[0]) != "device"
                    ])
            except Exception as err:
                LOGGER.error(f"Error reading {deviceName}: {err}")
            return {
                "device": deviceName,
                "address": str(device_address),
                "vendor": vendorName,
                "objects": objects,
            }

        queriedDevices = await asyncio.gather(*[
            queryDeviceObjects(device) for device in devices
        ])
        LOGGER.debug(f"Finished discovery of {len(queriedDevices)} devices")
        for device in queriedDevices:
            config = ComponentConfig(
                name=f"{device.get('device', 'Unknown').replace(' ', '-')}",
                api=str(Sensor.API),
                model="hipsterbrown:lutron-bacnet:lutron-sensor",
                attributes=dict_to_struct({
                    "address": device.get("address", "-"),
                    "vendor": device.get("vendor", "-"),
                    "objects": device.get("objects", []),
                }),
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
            del self.bacnet
