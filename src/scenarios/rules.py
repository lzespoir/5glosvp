from __future__ import annotations

from .models import CompatibilityRule, CompatibilityStatus

RULES = [
    CompatibilityRule(rule_id="RULE-HANDOVER-SINGLE-CELL", description_zh="切换需要至少两个候选小区", input_dimensions=["network_function", "topology"], result="INVALID_COMBINATION", reason_code="NO_NEIGHBOR_CELL", reason_zh="handover + single-cell 没有邻区"),
    CompatibilityRule(rule_id="RULE-STATIC-HANDOVER", description_zh="静态 UE 不构成切换业务场景", input_dimensions=["network_function", "mobility"], result="INVALID_COMBINATION", reason_code="STATIC_NO_HANDOVER", reason_zh="handover + static 不成立"),
    CompatibilityRule(rule_id="RULE-BEAM-TRAFFIC-ASSET", description_zh="波束空间流量需要研究团队模型", input_dimensions=["traffic"], result="REQUIRES_EXTERNAL_ASSET", reason_code="BEAM_TRAFFIC_MODEL_PENDING", reason_zh="beam_space_traffic 尚未接入真实模型"),
    CompatibilityRule(rule_id="RULE-MEASURED-TRAFFIC-ASSET", description_zh="实测流量需要外部数据资产", input_dimensions=["traffic"], result="REQUIRES_EXTERNAL_ASSET", reason_code="MEASURED_TRAFFIC_PENDING", reason_zh="measured_traffic 尚未绑定实测数据"),
    CompatibilityRule(rule_id="RULE-A-MATRIX-ASSET", description_zh="实测 A 矩阵需要明确语义并完成 adapter", input_dimensions=["device_antenna"], result="REQUIRES_EXTERNAL_ASSET", reason_code="A_MATRIX_ADAPTER_PENDING", reason_zh="A 矩阵仅完成数据契约与画像"),
    CompatibilityRule(rule_id="RULE-HANDOVER-IMPLEMENTATION", description_zh="切换语义先纳入目录，执行器待接入", input_dimensions=["network_function"], result="VALID_NOT_EXECUTABLE", reason_code="HANDOVER_NOT_EXECUTABLE", reason_zh="Handover 尚未接入执行后端"),
    CompatibilityRule(rule_id="RULE-MOBILE-IMPLEMENTATION", description_zh="移动 UE schema 已定义，动态 mobility 待接入", input_dimensions=["mobility"], result="VALID_NOT_EXECUTABLE", reason_code="MOBILITY_NOT_EXECUTABLE", reason_zh="动态 UE mobility 尚未接入"),
    CompatibilityRule(rule_id="RULE-NEIGHBOR-IMPLEMENTATION", description_zh="主邻区组合可表达但执行器待接入", input_dimensions=["topology"], result="VALID_NOT_EXECUTABLE", reason_code="NEIGHBOR_MODEL_PENDING", reason_zh="主小区/邻区模型待接入"),
]


def evaluate(dimensions: dict[str, str]) -> tuple[CompatibilityStatus, str, str]:
    if dimensions.get("network_function") == "handover" and dimensions.get("topology") == "single_site_single_cell":
        return "INVALID_COMBINATION", "NO_NEIGHBOR_CELL", "handover + single-cell 没有邻区"
    if dimensions.get("network_function") == "handover" and dimensions.get("mobility") == "static":
        return "INVALID_COMBINATION", "STATIC_NO_HANDOVER", "handover + static 不成立"
    if dimensions.get("traffic") == "beam_space_traffic":
        return "REQUIRES_EXTERNAL_ASSET", "BEAM_TRAFFIC_MODEL_PENDING", "beam_space_traffic 尚未接入真实模型"
    if dimensions.get("traffic") == "measured_traffic":
        return "REQUIRES_EXTERNAL_ASSET", "MEASURED_TRAFFIC_PENDING", "measured_traffic 尚未绑定实测数据"
    if dimensions.get("device_antenna") in {"measured_a_matrix_pending", "multi_beam_placeholder"}:
        return "REQUIRES_EXTERNAL_ASSET", "A_MATRIX_ADAPTER_PENDING", "A 矩阵/多波束 adapter 尚未完成"
    if dimensions.get("network_function") == "handover":
        return "VALID_NOT_EXECUTABLE", "HANDOVER_NOT_EXECUTABLE", "Handover 尚未接入执行后端"
    if dimensions.get("mobility") == "mobile":
        return "VALID_NOT_EXECUTABLE", "MOBILITY_NOT_EXECUTABLE", "动态 UE mobility 尚未接入"
    if dimensions.get("topology") == "main_neighbor_cells":
        return "VALID_NOT_EXECUTABLE", "NEIGHBOR_MODEL_PENDING", "主小区/邻区模型待接入"
    return "VALID_EXECUTABLE", "SUPPORTED_BASELINE", "当前组合可进入现有仿真/评估骨架"
