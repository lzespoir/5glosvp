"""
默认系统级后端注册 / Default system backend registration.
"""

from system_simulation.base import Capability, ModelType, SystemBackendDescriptor, SystemBackendRegistry
from system_simulation.fake_backend import FAKE_SYSTEM_BACKEND_ID, FakeSystemBackend

from .sionna_system_backend import PROVIDER, SIONNA_SYSTEM_BACKEND_ID, SionnaSystemBackend

SYSTEM_CAPABILITIES = (
    Capability.PROPAGATION,
    Capability.SYSTEM_SIMULATION,
    Capability.SCHEDULING,
    Capability.LINK_ADAPTATION,
    Capability.UE_METRICS,
    Capability.THROUGHPUT,
)


def default_system_registry(include_testing: bool = False) -> SystemBackendRegistry:
    """include_testing=True（TESTING=true）时才加入 FakeSystemBackend。"""
    registry = SystemBackendRegistry()
    registry.register(
        SystemBackendDescriptor(
            id=SIONNA_SYSTEM_BACKEND_ID,
            name_zh="Sionna 系统级仿真（RT + SYS）",
            name_en="Sionna System-Level Simulation (RT + SYS)",
            factory=SionnaSystemBackend,
            capabilities=SYSTEM_CAPABILITIES,
            model_type=ModelType.SIONNA_SYS,
            provider=PROVIDER,
        )
    )
    if include_testing:
        registry.register(
            SystemBackendDescriptor(
                id=FAKE_SYSTEM_BACKEND_ID,
                name_zh="系统级测试假后端（仅软件测试）",
                name_en="Fake System Backend (software testing only)",
                factory=FakeSystemBackend,
                capabilities=(Capability.SYSTEM_SIMULATION, Capability.UE_METRICS, Capability.THROUGHPUT),
                model_type=ModelType.TEST_FIXTURE,
                source_type="test_fixture",
                provider="fixture",
            )
        )
    return registry
