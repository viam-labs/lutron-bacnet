import asyncio
from typing import ClassVar, List, Mapping, Optional, Sequence, Tuple

from typing_extensions import Self
from viam.components.sensor import Sensor
from viam.components.switch import Switch
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.services.discovery import Discovery
from viam.utils import ValueTypes, dict_to_struct, struct_to_dict

from controller import BacnetController

SWITCHABLE_OBJECT_NAMES = [
    "Lighting Level",
    "Lighting State",
    "Daylighting Enabled",
    "Daylighting Level",
    "Occupied Level",
    "Unoccupied Level",
]


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
        self = super().new(config, dependencies)
        self.reconfigure(config, dependencies)
        return self

    @classmethod
    def validate_config(
        cls, config: ComponentConfig
    ) -> Tuple[Sequence[str], Sequence[str]]:
        """This method allows you to validate the configuration object received from the machine,
        as well as to return any implicit dependencies based on that `config`.

        Args:
            config (ComponentConfig): The configuration for this resource

        Returns:
            Sequence[str]: A list of implicit dependencies
        """
        return [], []

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
        self.logger.debug("Looking for resources")
        if self.bacnet is None:
            self.logger.warning("BacnetController not initialized")
            return []

        configs: List[ComponentConfig] = []

        try:
            await self.bacnet.client._discover()
            devices = await self.bacnet.client._devices(_return_list=True)
            self.logger.debug(
                f"Discovered the following devices (count: {len(self.bacnet.client.discoveredDevices or {})})"
            )
            self.logger.debug(devices)

            queriedDevices = await asyncio.gather(*[
                self.queryDeviceObjects(device) for device in devices
            ])

            self.logger.debug(f"Finished discovery of {len(queriedDevices)} devices")
            for device in queriedDevices:
                device_name = f"{device.get('device', 'Unknown').replace(' ', '-')}"
                device_objects = device.get("objects", [])
                config = ComponentConfig(
                    name=device_name,
                    api=str(Sensor.API),
                    model="hipsterbrown:lutron-bacnet:lutron-sensor",
                    attributes=dict_to_struct({
                        "address": device.get("address", "-"),
                        "vendor": device.get("vendor", "-"),
                        "objects": device_objects,
                    }),
                )
                configs.append(config)

                for obj in list(
                    filter(
                        lambda o: (o.get("name") in SWITCHABLE_OBJECT_NAMES),
                        device_objects,
                    )
                ):
                    obj_name = obj.get("name", "-")
                    configs.append(
                        ComponentConfig(
                            name=f"{obj_name.replace(' ', '-')}-{device_name}",
                            api=str(Switch.API),
                            model="hipsterbrown:lutron-bacnet:lutron-switch",
                            attributes=dict_to_struct({
                                "address": device.get("address", "-"),
                                "propAddress": obj.get("address", "-"),
                                "propType": obj.get("type", "-"),
                                "propName": obj_name,
                            }),
                        )
                    )
        except Exception as err:
            self.logger.error(f"Error trying to discover devices: {err}")

        return configs

    async def queryObjectDetails(self, deviceAddress, deviceObject):
        obj_type, obj_address = deviceObject
        baseQuery = f"{deviceAddress} {obj_type} {obj_address}"
        try:
            async with self.semaphore:
                objectName = await self.bacnet.client.read(f"{baseQuery} objectName")
                return {
                    "name": str(objectName),
                    "address": str(obj_address),
                    "type": str(obj_type),
                }
        except Exception as readErr:
            self.logger.error(
                f"Unable to get object name from {obj_type} at {obj_address}"
            )
            self.logger.error(readErr)
            return {
                "type": str(obj_type),
                "address": str(obj_address),
            }

    async def queryDeviceObjects(self, device):
        deviceName, vendorName, devId, device_address, _network_number = device
        objects = []
        try:
            objectList = await self.bacnet.client.read(
                f"{device_address} device {devId} objectList"
            )
            if objectList is not None:
                objects = await asyncio.gather(*[
                    self.queryObjectDetails(device_address, deviceObject)
                    for deviceObject in objectList
                    if str(deviceObject[0]) != "device"
                ])
        except Exception as err:
            self.logger.error(f"Error reading {deviceName}: {err}")
        return {
            "device": deviceName,
            "address": str(device_address),
            "vendor": vendorName,
            "objects": objects,
        }

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
            self.bacnet.release()
            self.bacnet = None
