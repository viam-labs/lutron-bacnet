from typing import Any, Dict, List, Mapping, Optional

from grpclib.client import Channel

from viam.proto.common import (
    DoCommandRequest,
    DoCommandResponse,
)
from viam.proto.component.switch import SwitchServiceStub
from viam.gen.component.switch.v1.switch_pb2 import (
    GetPositionRequest,
    GetPositionResponse,
    SetPositionRequest,
    GetNumberOfPositionsRequest,
    GetNumberOfPositionsResponse,
)
from viam.resource.rpc_client_base import ReconfigurableResourceRPCClientBase
from viam.utils import (
    ValueTypes,
    dict_to_struct,
    struct_to_dict,
)

from .switch import Switch


class SwitchClient(Switch, ReconfigurableResourceRPCClientBase):
    """
    gRPC client for Switch component
    """

    def __init__(self, name: str, channel: Channel):
        self.channel = channel
        self.client = SwitchServiceStub(channel)
        super().__init__(name)

    async def get_position(self) -> int:
        request = GetPositionRequest(name=self.name)
        response: GetPositionResponse = await self.client.GetPosition(request)
        return response.position

    async def set_position(self, position: int) -> None:
        request = SetPositionRequest(name=self.name, position=position)
        await self.client.SetPosition(request)

    async def get_number_of_positions(self) -> int:
        request = GetNumberOfPositionsRequest(name=self.name)
        response: GetNumberOfPositionsResponse = await self.client.GetPosition(request)
        return response.number_of_positions

    async def do_command(
        self,
        command: Mapping[str, ValueTypes],
        *,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Mapping[str, ValueTypes]:
        md = kwargs.get("metadata", self.Metadata()).proto
        request = DoCommandRequest(name=self.name, command=dict_to_struct(command))
        response: DoCommandResponse = await self.client.DoCommand(
            request, timeout=timeout, metadata=md
        )
        return struct_to_dict(response.result)
