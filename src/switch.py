from typing import ClassVar, Mapping, Optional, Sequence, Tuple, Any

from typing_extensions import Self
from viam.components.switch import Switch
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.utils import ValueTypes, struct_to_dict
from bacpypes3.basetypes import PropertyIdentifier
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier

from controller import BacnetController


class BacnetSensor(Switch, EasyResource):
    MODEL: ClassVar[Model] = Model(
        ModelFamily("hipsterbrown", "lutron-bacnet"), "lutron-switch"
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
        self.propName = str(attrs.get("propName", "N/A"))
        self.propAddress = str(attrs.get("propAddress", None))
        self.propType = str(attrs.get("propType", None))
        self.bacnet = BacnetController(logger=self.logger)
        return

    async def get_position(
        self,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> int:
        present_value = await self.get_present_value_for_object()
        if self.propType == "binary-value":
            return int(present_value)
        if self.propType == "analog-value":
            clamped_value = max(0, min(100, int(present_value)))
            return int(clamped_value // 20)
        return 0

    async def set_position(
        self,
        position: int,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> None:
        if self.propType == "binary-value":
            await self.update(position)
        if self.propType == "analog-value":
            clamped_value = max(0, min(4, int(position)))
            await self.update(int(clamped_value * 20))

    async def get_number_of_positions(
        self,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> int:
        if self.propType == "analog-value":
            return 5
        if self.propType == "binary-value":
            return 2
        return 0

    async def get_present_value_for_object(self):
        if self.bacnet is None:
            return None

        try:
            value = await self.bacnet.client.read(
                f"{self.address} {self.propType} {self.propAddress} presentValue"
            )
            return value
        except Exception as readErr:
            self.logger.error(f"Unable to get present value for {self.propName}")
            self.logger.error(readErr)
            return None

    async def update(self, value: int) -> bool:
        object_identifier = ObjectIdentifier((self.propType, self.propAddress))
        property_identifier = PropertyIdentifier("presentValue")
        device_address = Address(self.address)
        bacnet_app = self.bacnet.client.this_application.app

        await bacnet_app.write_property(
            address=device_address,
            objid=object_identifier,
            prop=property_identifier,
            value=value,
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
            self.logger.warning(f"Unknown command '{name}'")
        return result

    async def close(self):
        if self.bacnet:
            del self.bacnet
