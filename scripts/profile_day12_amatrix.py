from __future__ import annotations

import os
from pathlib import Path

from scenarios.amatrix import profile_directory


def main() -> None:
    source = Path(os.environ.get("DAY12_A_MATRIX_DIR", "/home/ubuntu/h2/sionnatest/webapp/data/a_matrix"))
    output = Path(__file__).resolve().parents[1] / "design" / "DAY12_A_MATRIX_DATA_PROFILE.md"
    artifacts = profile_directory(source)
    lines = [
        "# DAY12 A-Matrix Data Profile",
        "",
        "只读画像；未修改、覆盖、移动、归一化或提交原始 .npy。",
        "",
        "## Observed / 已观察事实",
        "",
        f"- Source directory: {source}（UI 不暴露此绝对路径）",
        f"- .npy file count: **{len(artifacts)}**",
        "- README.md 明确称文件为 SSB / CSI-RS 波束增益库；profiles.json 给出 AAU、beam type、beam id 等命名配置。",
        "- 配套 loader a_matrix_lib.py 直接以 (91, 72) 网格读取叶数组，并定义 elevation/azimuth 的 loader 常量；这证明 loader 约定，不自动证明原始测量轴语义。",
        "",
        "### File profile",
        "",
        "| file | bytes | sha256 | root dtype/shape | leaf arrays | leaf shape groups | leaf dtype groups | NaN/Inf | complex | value summary |",
        "|---|---:|---|---|---:|---|---|---|---|---|",
    ]
    for item in artifacts:
        lines.append(
            f"| {item.file_name} | {item.file_size} | {item.file_hash} | {item.numpy_dtype} / {item.numpy_shape} | {item.leaf_arrays} | {item.leaf_shape_groups} | {item.leaf_dtype_groups} | {item.contains_nan}/{item.contains_inf} | {item.is_complex} | {item.observed_value_summary} |"
        )
    lines += [
        "",
        "### Cross-file summary",
        "",
        f"- Shape groups: {sorted({shape for item in artifacts for shape in item.leaf_shape_groups})}；两个 object-dtype 根对象的叶数组均为 [91, 72]。",
        f"- Dtype groups: {sorted({dtype for item in artifacts for dtype in item.leaf_dtype_groups})}；叶数组为 float64。",
        "- Complex arrays: NO（观察到的叶数组为实数 float64）。",
        "- Naming patterns: a_matrix_spread.npy、a_matrix_phase_power.npy；README 将其对应为 8-beam 与 7-beam 族，但该命名不替代设备/轴语义确认。",
        "- Identical hashes: none observed between the two files.",
        "",
        "## Likely Interpretation / 可能解释",
        "",
        "- 两个文件是嵌套 dict/object 容器，叶数组均为 91×72 的实数网格；名称与 loader 表明它们被现有 webapp 当作 SSB/CSI-RS 多波束库使用。",
        "- profiles.json 中的 beam_ids 和 aau_type 支持“可能存在设备/波束族分组”的解释；这是命名与索引规律，不是对原始矩阵数学轴的确认。",
        "",
        "## Questions for Data Owner / 待确认",
        "",
        "- 每个 axis 的正式含义、采样顺序和球面坐标定义；",
        "- 角度单位、测量坐标系、极化和频点；",
        "- 数值究竟是 gain、power、amplitude、校准值还是其他测量量；",
        "- 是否归一化、是否校准、设备型号与文件/entry 的正式映射；",
        "- 最后一维或 entry key 是否可被称为 beam，以及多设备/多波束分组的权威 metadata。",
        "",
        "## Boundary",
        "",
        "本轮只建立 AMatrixArtifact 契约和只读画像；没有把 A 矩阵换算为 gain/RSRP/SINR，也没有把它解释成 UE-Cell Association Matrix。下一步 adapter 必须先获得上述数据语义确认。",
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
