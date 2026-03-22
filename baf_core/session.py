import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import BAFConfig
from .policies import BAFPolicyState, compute_risk_delta, update_level


@dataclass
class BAFClassificationResult:
    kind: str
    value: str
    category: str
    risk_score: float
    meta: Dict[str, Any]


class BAFSession:
    def __init__(self, config: BAFConfig, agent_id: str = "exam_helper", session_id: Optional[str] = None):
        self.config = config
        raw = config.raw

        self.agent_id = agent_id
        self.session_id = session_id or datetime.utcnow().strftime("%Y%m%d%H%M%S")

        self.paths: Dict[str, Any] = raw.get("paths", {})
        self.domains: Dict[str, Any] = raw.get("domains", {})
        self.risk_rules: Dict[str, Any] = raw.get("risk_rules", {})
        self.thresholds: Dict[str, Any] = raw.get("thresholds", {})
        self.profiles: Dict[str, Any] = raw.get("profiles", {})

        # Per-session risk/level state
        self.state = BAFPolicyState()

        # Simple CSV log sink
        logs_root = Path("logs")
        logs_root.mkdir(exist_ok=True)
        self.log_path = logs_root / f"baf_session_{self.session_id}.csv"
        if not self.log_path.exists():
            with self.log_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "timestamp",
                        "session_id",
                        "agent_id",
                        "action",
                        "resource",
                        "profile",
                        "matched_group",
                        "base_rule",
                        "output_mode",
                        "score_delta",
                        "risk_score",
                        "level",
                        "decision",
                    ]
                )

    def _log_event(
        self,
        action: str,
        resource: str,
        profile: Optional[str],
        matched_group: Optional[str],
        base_rule: Optional[str],
        score_delta: int,
        decision: str,
        output_mode: str = "",
    ) -> None:
        with self.log_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    datetime.utcnow().isoformat(),
                    self.session_id,
                    self.agent_id,
                    action,
                    resource,
                    profile or "",
                    matched_group or "",
                    base_rule or "",
                    output_mode,
                    score_delta,
                    self.state.risk_score,
                    self.state.level,
                    decision,
                ]
            )

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
        # To be extended later if you want a BAFClassificationResult for domains
        return BAFClassificationResult(
            kind="domain",
            value=domain,
            category="unknown",
            risk_score=0.0,
            meta={"profile": profile},
        )

    # === Helpers for Day V3 ===

    def _categorize_domain(self, url: str) -> str:
        """Return domain category: internal_known or external_unknown."""
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            host = parsed.netloc
            if not host:
                return "none"
            internal = set(self.domains.get("internal_trusted", []))
            if host in internal:
                return "internal_known"
            return "external_unknown"
        except Exception:
            return "none"

    # === New Day V3 wrappers ===

    def list_dir(self, path: str, profile: Optional[str] = None) -> List[str]:
        result = self.classify_path(path, profile=profile)

        # Map group to action
        if result.meta.get("matched_group") == "secrets":
            action_key = "read_secrets"
        elif result.meta.get("matched_group") == "personal":
            action_key = "read_personal"
        else:
            action_key = "read_other"

        score_delta = compute_risk_delta(action_key, {"risk_rules": self.risk_rules})
        self.state.risk_score = min(100, self.state.risk_score + score_delta)
        update_level(self.state, self.thresholds)

        decision = "allow"
        if self.state.level == "L0" and result.meta.get("matched_group") in ("secrets", "personal"):
            decision = "block"

        self._log_event(
            action="list_dir",
            resource=path,
            profile=profile,
            matched_group=result.meta.get("matched_group"),
            base_rule=result.meta.get("base_rule"),
            score_delta=score_delta,
            decision=decision,
            output_mode="",
        )

        if decision == "block":
            raise PermissionError(f"BAF blocked list_dir on {path} at level {self.state.level}")

        p = Path(path).expanduser()
        return [str(child) for child in p.iterdir()]

    def read_file(self, path: str, profile: Optional[str] = None) -> str:
        result = self.classify_path(path, profile=profile)

        if result.meta.get("matched_group") == "secrets":
            action_key = "read_secrets"
        elif result.meta.get("matched_group") == "personal":
            action_key = "read_personal"
        else:
            action_key = "read_other"

        score_delta = compute_risk_delta(action_key, {"risk_rules": self.risk_rules})
        self.state.risk_score = min(100, self.state.risk_score + score_delta)
        update_level(self.state, self.thresholds)

        decision = "allow"
        if self.state.level == "L0" and result.meta.get("matched_group") in ("secrets", "personal"):
            decision = "block"

        self._log_event(
            action="read_file",
            resource=path,
            profile=profile,
            matched_group=result.meta.get("matched_group"),
            base_rule=result.meta.get("base_rule"),
            score_delta=score_delta,
            decision=decision,
            output_mode="raw",
        )

        if decision == "block":
            raise PermissionError(f"BAF blocked read_file on {path} at level {self.state.level}")

        p = Path(path).expanduser()
        return p.read_text(encoding="utf-8", errors="ignore")

    # === Day V5: output modes / Presenter-style safe_read_file ===

    def safe_read_file(self, path: str, profile: Optional[str] = None, mode: Optional[str] = None) -> Any:
        """
        Like read_file, but enforces an output mode:
        - raw: full content (current behaviour)
        - metadata: only basic file metadata
        - redacted: simple PII masking (placeholder)
        - summary: first N characters as pseudo-summary (placeholder)
        """
        tools_cfg = self.config.raw.get("tools", {})
        file_read_cfg = tools_cfg.get("file_read", {})
        profile_overrides = file_read_cfg.get("profiles", {})

        effective_mode = mode or profile_overrides.get(profile or "", file_read_cfg.get("default_mode", "raw"))

        result = self.classify_path(path, profile=profile)

        if result.meta.get("matched_group") == "secrets":
            action_key = "read_secrets"
        elif result.meta.get("matched_group") == "personal":
            action_key = "read_personal"
        else:
            action_key = "read_other"

        score_delta = compute_risk_delta(action_key, {"risk_rules": self.risk_rules})
        self.state.risk_score = min(100, self.state.risk_score + score_delta)
        update_level(self.state, self.thresholds)

        decision = "allow"
        if self.state.level == "L0" and result.meta.get("matched_group") in ("secrets", "personal"):
            decision = "block"

        self._log_event(
            action="safe_read_file",
            resource=path,
            profile=profile,
            matched_group=result.meta.get("matched_group"),
            base_rule=result.meta.get("base_rule"),
            score_delta=score_delta,
            decision=decision,
            output_mode=effective_mode,
        )

        if decision == "block":
            raise PermissionError(f"BAF blocked safe_read_file on {path} at level {self.state.level}")

        p = Path(path).expanduser()

        if effective_mode == "metadata":
            stat = p.stat()
            return {
                "mode": "metadata",
                "name": p.name,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
            }

        text = p.read_text(encoding="utf-8", errors="ignore")

        if effective_mode == "redacted":
            import re

            redacted = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "[EMAIL]", text)
            redacted = re.sub(r"\b\d{4,}\b", "[NUM]", redacted)
            return {"mode": "redacted", "content": redacted}

        if effective_mode == "summary":
            return {"mode": "summary", "content": text[:500]}

        return {"mode": "raw", "content": text}

    def http_post(self, url: str, data: str, profile: Optional[str] = None):
        """
        HTTP POST with BAF enforcement and logging.
        """
        import requests

        domain_category = self._categorize_domain(url)
        nbytes = len(data.encode("utf-8", errors="ignore"))

        # Determine logical action keys for risk
        action_keys: List[str] = []
        if domain_category == "external_unknown":
            action_keys.append("external_http")

        threshold = int(self.risk_rules.get("http_post_large_threshold", 10240))
        if nbytes > threshold:
            action_keys.append("large_http_post")

        # Compute combined risk delta
        score_delta = 0
        for key in action_keys:
            score_delta += compute_risk_delta(key, {"risk_rules": self.risk_rules})

        if score_delta:
            self.state.risk_score = min(100, self.state.risk_score + score_delta)
            update_level(self.state, self.thresholds)

        # Enforcement rules (similar spirit to v1)
        decision = "allow"
        if self.state.level in {"L1", "L2"} and domain_category == "external_unknown":
            decision = "block"
        if self.state.level == "L0":
            decision = "block"

        self._log_event(
            action="http_post",
            resource=url,
            profile=profile,
            matched_group=None,
            base_rule=",".join(action_keys) if action_keys else "",
            score_delta=score_delta,
            decision=decision,
            output_mode="",
        )

        if decision == "block":
            raise PermissionError(f"BAF blocked http_post to {url} at level {self.state.level}")

        resp = requests.post(url, data=data)
        return resp
