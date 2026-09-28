from .models import ResearchAlgorithmReference


RESEARCH_CATALOG = [
    ResearchAlgorithmReference(
        reference_id="ZO-PGD",
        algorithm_family="zero-order policy gradient",
        paper_title="Zeroth-Order Policy Optimization for Black-Box Network Control",
        authors=["Research candidate"], year=2024,
        problem_types=["continuous_network_parameter"],
        parameter_types=["continuous", "vector"], requires_training=False, black_box=True,
        implementation_status="not_integrated",
        notes="Catalog reference only; deliberately not forced onto categorical user association.",
        source="internal research catalog",
    ),
    ResearchAlgorithmReference(
        reference_id="SOLUTION-MAPPING-L2O",
        algorithm_family="solution mapping / learning to optimize",
        paper_title="Learning to Optimize Combinatorial Network Decisions",
        authors=["Research candidate"], year=2024,
        problem_types=["mixed_network_optimization"],
        parameter_types=["mixed", "categorical_vector"], requires_training=True, black_box=True,
        implementation_status="not_integrated",
        notes="Research candidate; no runnable implementation is registered.",
        source="internal research catalog",
    ),
    ResearchAlgorithmReference(
        reference_id="LEARNING-ASSISTED-BNB",
        algorithm_family="learning-assisted branch-and-bound",
        paper_title="Learning-Assisted Branch-and-Bound for Resource Management",
        authors=["Research candidate"], year=2024,
        problem_types=["mixed_integer_resource_management"],
        parameter_types=["integer", "categorical", "mixed"], requires_training=True, black_box=False,
        implementation_status="not_integrated",
        notes="Future candidate; platform must not present it as an official implementation.",
        source="internal research catalog",
    ),
]
