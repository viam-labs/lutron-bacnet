import asyncio
from typing import ClassVar, Dict, Mapping, Optional, Sequence, Any

from typing_extensions import Self
from viam.components.sensor import Sensor
from viam.logging import getLogger
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.utils import SensorReading, ValueTypes, struct_to_dict

import BAC0
from controller import BacnetController

LOGGER = getLogger("lutron-bacnet:sensor")


class BacnetSensor(Sensor, EasyResource):
    MODEL: ClassVar[Model] = Model(
        ModelFamily("hipsterbrown", "lutron-bacnet"), "lutron-sensor"
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
        self.address = str(attrs.get("address", "0:0x00"))

        self.networkId, self.deviceID = self.address.split(":")
        self.deviceID = int(self.deviceID, 16)
        LOGGER.info(
            f"Current address: {self.address}; current device ID: {self.deviceID}"
        )
        self.objectList = list(attrs.get("objects", []))
        self.bacnet = BacnetController()
        # object_list = [
        #     (obj.get("type"), int(obj.get("address"))) for obj in self.objectList
        # ]
        # self.device = asyncio.run(
        #     BAC0.device(
        #         address=self.address,
        #         network=self.bacnet.client,
        #         object_list=object_list,
        #     )
        # )
        return

    async def get_readings(
        self,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Mapping[str, SensorReading]:
        readings = await asyncio.gather(*[
            self.get_present_value_for_object(deviceObject)
            for deviceObject in self.objectList
        ])
        return {reading["name"]: reading for reading in readings}

    async def get_present_value_for_object(self, deviceObject: Dict):
        if self.bacnet is None:
            return deviceObject | {"presentValue": "N/A"}

        try:
            value = await self.bacnet.client.read(
                f"{self.address} {deviceObject.get('type')} {deviceObject.get('address')} presentValue"
            )
            return deviceObject | {"presentValue": value}
        except Exception as readErr:
            LOGGER.error(f"Unable to get present value for {deviceObject.get('name')}")
            LOGGER.error(readErr)
            return deviceObject | {"presentValue": "N/A"}

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
