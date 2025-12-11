import asyncio
from typing import ClassVar, Dict, Mapping, Optional, Sequence, Any, Tuple

from typing_extensions import Self
from viam.components.sensor import Sensor
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.utils import SensorReading, ValueTypes, struct_to_dict
from bacpypes3.basetypes import PropertyIdentifier
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier

from controller import BacnetController


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
        self.address = str(attrs.get("address", "0:0x00"))

        self.networkId, self.deviceID = self.address.split(":")
        self.deviceID = int(self.deviceID, 16)
        self.logger.info(
            f"Current address: {self.address}; current device ID: {self.deviceID}"
        )
        self.objectList = list(attrs.get("objects", []))
        self.bacnet = BacnetController(logger=self.logger)
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
            self.logger.error(
                f"Unable to get present value for {deviceObject.get('name')}"
            )
            self.logger.error(readErr)
            return deviceObject | {"presentValue": "N/A"}

    async def update(self, deviceObject: Dict) -> bool:
        if deviceObject.get("address", None):
            obj = [
                obj
                for obj in self.objectList
                if obj.get("address") == deviceObject.get("address")
            ].pop()
        elif deviceObject.get("name", None):
            obj = [
                obj
                for obj in self.objectList
                if obj.get("name") == deviceObject.get("name")
            ].pop()
        else:
            raise Exception("Please provide the object name or address to update.")

        object_identifier = ObjectIdentifier((obj.get("type"), obj.get("address")))
        property_identifier = PropertyIdentifier("presentValue")
        device_address = Address(self.address)
        bacnet_app = self.bacnet.client.this_application.app

        await bacnet_app.write_property(
            address=device_address,
            objid=object_identifier,
            prop=property_identifier,
            value=deviceObject.get("value"),
            priority=16,
        )
        return True

    async def do_command(
        self,
        command: Mapping[str, ValueTypes],
        *,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Mapping[str, ValueTypes]:
        result = {key: False for key in command.keys()}
        for name, args in command.items():
            if name == "update":
                response = await self.update(dict(args))
                result[name] = response
            else:
                self.logger.warning(f"Unknown command '{name}'")
        return result

    async def close(self):
        if self.bacnet:
            del self.bacnet
