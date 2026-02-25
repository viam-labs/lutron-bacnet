from typing import Any, ClassVar, List, Mapping, Optional, Sequence, Tuple

from typing_extensions import Self
from viam.app.viam_client import ViamClient
from viam.components.button import Button
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.services.discovery import Discovery
from viam.utils import ValueTypes, struct_to_dict

LUTRON_MODEL_PREFIX = "hipsterbrown:lutron-bacnet:lutron-"

class DiscoveryButton(Button, EasyResource):
    MODEL: ClassVar[Model] = Model(
        ModelFamily("hipsterbrown", "lutron-bacnet"), "discovery-button"
    )

    discovery: Discovery
    machine_part_id: str
    capture_frequency_hz: float
    _last_config: Optional[List[dict]]

    @classmethod
    def new(
        cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ) -> Self:
        self = super().new(config, dependencies)
        self.reconfigure(config, dependencies)
        return self

    @classmethod
    def validate_config(
        cls, config: ComponentConfig
    ) -> Tuple[Sequence[str], Sequence[str]]:
        attrs = struct_to_dict(config.attributes)
        discovery_service = attrs.get("discovery_service")
        if not discovery_service:
            raise ValueError("discovery_service attribute is required")
        machine_part_id = attrs.get("machine_part_id")
        if not machine_part_id:
            raise ValueError("machine_part_id attribute is required")
        implicit_deps = [f"rdk:service:discovery/{discovery_service}"]
        return implicit_deps, []

    def reconfigure(
        self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ):
        attrs = struct_to_dict(config.attributes)
        self.machine_part_id = str(attrs.get("machine_part_id", ""))
        self.capture_frequency_hz = float(attrs.get("capture_frequency_hz", 0))
        self._last_config = None

        discovery_service_name = str(attrs.get("discovery_service", ""))
        discovery_resource_name = ResourceName(
            namespace="rdk",
            type="service",
            subtype="discovery",
            name=discovery_service_name,
        )
        self.discovery = dependencies[discovery_resource_name]  # type: ignore

    async def push(
        self,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> None:
        self.logger.info("Discovery button pushed — starting device discovery")

        discovered: List[ComponentConfig] = await self.discovery.discover_resources()
        self.logger.info(f"Discovered {len(discovered)} component configs")

        new_components = [self._component_config_to_dict(c) for c in discovered]
        self._last_config = new_components

        viam_client = await ViamClient.create_from_env_vars()
        try:
            app = viam_client.app_client
            part = await app.get_robot_part(self.machine_part_id)
            current_config: dict = dict(part.robot_config or {})

            existing_components: List[dict] = list(
                current_config.get("components", [])
            )
            preserved = [
                c for c in existing_components
                if not str(c.get("model", "")).startswith(LUTRON_MODEL_PREFIX)
            ]
            merged_components = preserved + new_components

            merged_config = dict(current_config)
            merged_config["components"] = merged_components

            await app.update_robot_part(
                robot_part_id=self.machine_part_id,
                name=part.name,
                robot_config=merged_config,
            )
            self.logger.info(
                f"Machine config updated: {len(new_components)} discovered components applied"
            )
        finally:
            viam_client.close()

    def _component_config_to_dict(self, config: ComponentConfig) -> dict:
        entry: dict = {
            "name": config.name,
            "api": config.api,
            "model": config.model,
            "attributes": struct_to_dict(config.attributes),
        }
        if self.capture_frequency_hz > 0 and "sensor" in config.api:
            entry["service_configs"] = [
                {
                    "type": "data_manager",
                    "attributes": {
                        "capture_methods": [
                            {
                                "method": "Readings",
                                "capture_frequency_hz": self.capture_frequency_hz,
                                "disabled": False,
                                "additional_params": {},
                            }
                        ]
                    },
                }
            ]
        return entry

    async def do_command(
        self,
        command: Mapping[str, ValueTypes],
        *,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Mapping[str, ValueTypes]:
        result: dict = {key: False for key in command.keys()}
        for name, _args in command.items():
            if name == "get_last_config":
                result[name] = self._last_config or []
            else:
                self.logger.warning(f"Unknown command '{name}'")
        return result

    async def close(self):
        pass
