from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class BAFPolicyState:
    """Per-session risk and level."""
    risk_score: int = 0  # 0–100
    level: str = "L2"    # L2 (low), L1 (medium), L0 (high)


def compute_risk_delta(action: str, context: Dict[str, Any]) -> int:
    """
    Map a logical action type to a risk increment.
    """
    risk_rules: Dict[str, Any] = context.get("risk_rules", {})

    if action == "read_personal":
        return int(risk_rules.get("personal_read", 0))
    if action == "read_secrets":
        return int(risk_rules.get("secrets_read", 0))
    if action == "external_http":
        return int(risk_rules.get("external_unknown_http", 0))
    if action == "large_http_post":
        return int(risk_rules.get("http_post_large_bytes", 0))

    return 0


def update_level(state: BAFPolicyState, thresholds: Dict[str, Any]) -> None:
    """Update L2/L1/L0 based on current risk_score."""
    l2_to_l1 = int(thresholds.get("L2_to_L1", 40))
    l1_to_l0 = int(thresholds.get("L1_to_L0", 80))

    if state.risk_score >= l1_to_l0:
        state.level = "L0"
    elif state.risk_score >= l2_to_l1:
        state.level = "L1"
    else:
        state.level = "L2"
