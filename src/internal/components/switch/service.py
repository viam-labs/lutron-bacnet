from grpclib.server import Stream

from viam.proto.common import (
    DoCommandRequest,
    DoCommandResponse,
)
from viam.gen.component.switch.v1.switch_pb2 import (
    GetPositionRequest,
    GetPositionResponse,
    SetPositionRequest,
    SetPositionResponse,
    GetNumberOfPositionsRequest,
    GetNumberOfPositionsResponse,
)
from viam.proto.component.switch import SwitchServiceBase
from viam.resource.rpc_service_base import ResourceRPCServiceBase
from viam.utils import dict_to_struct, struct_to_dict

from .switch import Switch


class SwitchRPCService(SwitchServiceBase, ResourceRPCServiceBase[Switch]):
    """
    gRPC Service for a generic Switch
    """

    RESOURCE_TYPE = Switch

    async def GetPosition(
        self, stream: Stream[GetPositionRequest, GetPositionResponse]
    ) -> None:
        request = await stream.recv_message()
        assert request is not None
        name = request.name
        switch = self.get_resource(name)
        position = await switch.get_position()
        response = GetPositionResponse(position=position)
        await stream.send_message(response)

    async def SetPosition(
        self, stream: Stream[SetPositionRequest, SetPositionResponse]
    ) -> None:
        request = await stream.recv_message()
        assert request is not None
        name = request.name
        switch = self.get_resource(name)
        await switch.set_position(position=request.position)
        response = SetPositionResponse()
        await stream.send_message(response)

    async def GetNumberOfPositions(
        self, stream: Stream[GetNumberOfPositionsRequest, GetNumberOfPositionsResponse]
    ) -> None:
        request = await stream.recv_message()
        assert request is not None
        name = request.name
        switch = self.get_resource(name)
        number_of_positions = await switch.get_number_of_positions()
        response = GetNumberOfPositionsResponse(number_of_positions=number_of_positions)
        await stream.send_message(response)

    async def DoCommand(
        self, stream: Stream[DoCommandRequest, DoCommandResponse]
    ) -> None:
        request = await stream.recv_message()
        assert request is not None
        name = request.name
        switch = self.get_resource(name)
        timeout = stream.deadline.time_remaining() if stream.deadline else None
        result = await switch.do_command(
            command=struct_to_dict(request.command),
            timeout=timeout,
            metadata=stream.metadata,
        )
        response = DoCommandResponse(result=dict_to_struct(result))
        await stream.send_message(response)
