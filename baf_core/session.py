from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import BAFConfig


@dataclass
class BAFClassificationResult:
    kind: str
    value: str
    category: str
    risk_score: float
    meta: Dict[str, Any]


class BAFSession:
    def __init__(self, config: BAFConfig):
        self.config = config
        raw = config.raw

        self.paths: Dict[str, Any] = raw.get("paths", {})
        self.domains: Dict[str, Any] = raw.get("domains", {})
        self.risk_rules: Dict[str, Any] = raw.get("risk_rules", {})
        self.thresholds: Dict[str, Any] = raw.get("thresholds", {})
        self.profiles: Dict[str, Any] = raw.get("profiles", {})

    def _profile_use_paths(self, profile: Optional[str]) -> List[str]:
        if not profile:
            return []
        prof_cfg = self.profiles.get(profile, {})
        return list(prof_cfg.get("use_paths", []))

    def _score_to_risk(self, score: int) -> float:
        # convert 0–100 to 0.0–1.0
        return max(0.0, min(1.0, score / 100.0))

    def _apply_thresholds(self, score: int) -> str:
        # use your thresholds: L2_to_L1, L1_to_L0
        l2_to_l1 = int(self.thresholds.get("L2_to_L1", 40))
        l1_to_l0 = int(self.thresholds.get("L1_to_L0", 80))

        if score >= l1_to_l0:
            return "L0"  # highest risk
        if score >= l2_to_l1:
            return "L1"
        return "L2"      # lowest risk

    def classify_path(self, path: str, profile: Optional[str] = None) -> BAFClassificationResult:
        """
        Simple semantics:
        - If path falls under any group listed in profile.use_paths, map that group to a risk rule.
        - Currently:
            secrets -> secrets_read
            personal -> personal_read
        - Otherwise: treated as low risk.
        """
        use_paths = self._profile_use_paths(profile)
        p = Path(path).expanduser().resolve()

        matched_group: Optional[str] = None
        matched_root: Optional[str] = None

        # Normalize configured paths to absolute for comparison
        for group_name, cfg in self.paths.items():
            # cfg can be a string or a list
            dirs: List[str]
            if isinstance(cfg, str):
                dirs = [cfg]
            else:
                dirs = list(cfg)

            for d in dirs:
                root = Path(d).expanduser().resolve()
                try:
                    p.relative_to(root)
                    matched_group = group_name
                    matched_root = str(root)
                    break
                except ValueError:
                    continue
            if matched_group:
                break

        # default score: 0 (L2)
        score = 0
        base_rule = None

        if matched_group and matched_group in use_paths:
            if matched_group == "secrets":
                base_rule = "secrets_read"
            elif matched_group == "personal":
                base_rule = "personal_read"

        if base_rule and base_rule in self.risk_rules:
            score = int(self.risk_rules[base_rule])

        category = self._apply_thresholds(score)
        risk = self._score_to_risk(score)

        return BAFClassificationResult(
            kind="path",
            value=str(p),
            category=category,
            risk_score=risk,
            meta={
                "profile": profile,
                "matched_group": matched_group,
                "matched_root": matched_root,
                "base_rule": base_rule,
                "score": score,
            },
        )

    def classify_domain(self, domain: str, profile: Optional[str] = None) -> BAFClassificationResult:
        # To be implemented later using `domains` and `risk_rules.external_unknown_http`, etc.
        return BAFClassificationResult(
            kind="domain",
            value=domain,
            category="unknown",
            risk_score=0.0,
            meta={"profile": profile},
        )
