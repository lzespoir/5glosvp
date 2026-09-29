from __future__ import annotations

from .models import ScenarioTaxonomy, TaxonomyDimension, TaxonomyOption

TAXONOMY_VERSION = "0.1"


def _dimension(key: str, zh: str, en: str, options: list[tuple[str, str, str, str]]) -> TaxonomyDimension:
    return TaxonomyDimension(
        key=key,
        label_zh=zh,
        label_en=en,
        options=[TaxonomyOption(value=v, label_zh=lz, label_en=le, status=status) for v, lz, le, status in options],
    )


def build_taxonomy() -> ScenarioTaxonomy:
    return ScenarioTaxonomy(
        taxonomy_version=TAXONOMY_VERSION,
        dimensions=[
            _dimension("environment", "环境", "Environment", [
                ("dense_urban", "密集城区", "Dense urban", "SUPPORTED"), ("urban", "一般城区", "Urban", "SUPPORTED"),
                ("residential", "住宅区", "Residential", "SUPPORTED"), ("cbd", "CBD/商务区", "CBD", "SUPPORTED"),
                ("transport", "交通/道路", "Transport", "PARTIAL"), ("hotspot", "热点区域", "Hotspot", "PARTIAL"),
                ("mixed_urban", "混合城区", "Mixed urban", "PARTIAL"),
            ]),
            _dimension("topology", "网络拓扑", "Network topology", [
                ("single_site_single_cell", "单站单小区", "Single site / cell", "SUPPORTED"),
                ("single_site_multi_cell", "单站多小区", "Single site / multi-cell", "SUPPORTED"),
                ("multi_site_multi_cell", "多站多小区", "Multi-site / multi-cell", "PARTIAL"),
                ("macro_dominant", "宏站主导", "Macro dominant", "PARTIAL"),
                ("main_neighbor_cells", "主小区+邻区", "Serving + neighbor cells", "DEFINED_NOT_EXECUTABLE"),
            ]),
            _dimension("ue_population", "UE 群体", "UE population", [
                ("low", "低密度", "Low density", "SUPPORTED"), ("medium", "中密度", "Medium density", "SUPPORTED"),
                ("high", "高密度", "High density", "SUPPORTED"),
            ]),
            _dimension("mobility", "移动性", "Mobility", [
                ("static", "静态", "Static", "SUPPORTED"), ("mobile", "移动", "Mobile", "PLANNED"),
            ]),
            _dimension("traffic", "流量", "Traffic", [
                ("full_buffer", "全缓存", "Full buffer", "SUPPORTED"), ("low_load", "低负载", "Low load", "SUPPORTED"),
                ("medium_load", "中负载", "Medium load", "SUPPORTED"), ("high_load", "高负载", "High load", "SUPPORTED"),
                ("hotspot_traffic", "热点流量", "Hotspot traffic", "PARTIAL"), ("time_varying", "时变流量", "Time varying", "PARTIAL"),
                ("beam_space_traffic", "波束空间流量", "Beam-space traffic", "EXTERNAL_MODEL_REQUIRED"),
                ("measured_traffic", "实测流量", "Measured traffic", "REQUIRES_EXTERNAL_DATA"),
            ]),
            _dimension("radio_condition", "无线条件", "Radio condition", [
                ("coverage_normal", "正常覆盖", "Normal coverage", "SUPPORTED"), ("coverage_weak", "弱覆盖", "Weak coverage", "PARTIAL"),
                ("interference_low", "低干扰", "Low interference", "SUPPORTED"), ("interference_medium", "中干扰", "Medium interference", "PARTIAL"),
                ("interference_high", "强干扰", "High interference", "PARTIAL"),
            ]),
            _dimension("network_function", "网络功能", "Network function", [
                ("coverage", "覆盖", "Coverage", "SUPPORTED"), ("user_access", "用户接入", "User access", "SUPPORTED"),
                ("load_balancing", "负载均衡", "Load balancing", "PARTIAL"), ("resource_scheduling", "资源调度", "Resource scheduling", "PARTIAL"),
                ("handover", "切换", "Handover", "PLANNED"), ("interference_coordination", "干扰协调", "Interference coordination", "PARTIAL"),
            ]),
            _dimension("optimization_problem", "优化问题", "Optimization problem", [
                ("NETWORK_STRUCTURE", "网络结构参数", "Network structure", "SUPPORTED"),
                ("USER_ACCESS", "用户接入参数", "User access", "SUPPORTED"),
                ("SYSTEM_RESOURCE", "系统资源参数", "System resource", "PARTIAL"),
            ]),
            _dimension("device_antenna", "设备/天线", "Device / antenna", [
                ("generic_simulation", "通用仿真设备", "Generic simulation device", "SUPPORTED"),
                ("measured_a_matrix_pending", "实测 A 矩阵（待适配）", "Measured A-matrix pending adapter", "REQUIRES_EXTERNAL_DATA"),
                ("multi_beam_placeholder", "多波束契约占位", "Multi-beam contract placeholder", "EXTERNAL_MODEL_REQUIRED"),
            ]),
        ],
        families=[
            {"value": "coverage_structure", "label_zh": "覆盖与结构", "label_en": "Coverage & Structure"},
            {"value": "user_access_load", "label_zh": "用户接入与负载", "label_en": "User Access & Load"},
            {"value": "resource_scheduling", "label_zh": "资源调度", "label_en": "Resource Scheduling"},
            {"value": "mobility_handover", "label_zh": "移动与切换", "label_en": "Mobility & Handover"},
            {"value": "traffic_hotspot", "label_zh": "流量热点", "label_en": "Traffic Hotspot"},
            {"value": "interference", "label_zh": "干扰", "label_en": "Interference"},
            {"value": "beam_antenna", "label_zh": "波束与天线", "label_en": "Beam & Antenna"},
            {"value": "mixed", "label_zh": "混合", "label_en": "Mixed"},
        ],
    )


TAXONOMY = build_taxonomy()


def option_labels() -> dict[str, dict[str, tuple[str, str]]]:
    return {d.key: {o.value: (o.label_zh, o.label_en) for o in d.options} for d in TAXONOMY.dimensions}
