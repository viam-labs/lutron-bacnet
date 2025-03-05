import abc
from typing import Final

from viam.resource.types import API, RESOURCE_NAMESPACE_RDK, RESOURCE_TYPE_COMPONENT
from viam.components.component_base import ComponentBase


class Switch(ComponentBase):
    """
    Switch represents a device with two or more finite states (or positions) than can be set and retrieved.
    """

    API: Final = API(RESOURCE_NAMESPACE_RDK, RESOURCE_TYPE_COMPONENT, "switch")

    @abc.abstractmethod
    async def get_position(self) -> int:
        """
        Returns the current position of the switch.
        """
        ...

    @abc.abstractmethod
    async def set_position(self, position: int) -> None:
        """
        Sets the current position of the switch. Return None;
        """
        ...

    @abc.abstractmethod
    async def get_number_of_positions(self) -> int:
        """
        Returns the total number of valid positions for the switch.
        """
        ...
