# baf_core/session.py

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
    def __init__(
        self,
        config: BAFConfig,
        agent_id: str = "exam_helper",
        session_id: Optional[str] = None,
        session_label: Optional[str] = None,
    ):
        self.config = config
        raw = config.raw

        self.agent_id = agent_id
        self.session_id = session_id or datetime.utcnow().strftime("%Y%m%d%H%M%S")
        self.session_label: Optional[str] = session_label

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
                        "schema_version",
                        "timestamp",
                        "session_id",
                        "agent_id",
                        "session_label",
                        "action",
                        "resource",
                        "profile",
                        "matched_group",
                        "base_rule",
                        "domain_category",
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
        domain_category: str = "",
    ) -> None:
        with self.log_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "v1",  # schema_version
                    datetime.utcnow().isoformat() + "Z",
                    self.session_id,
                    self.agent_id,
                    self.session_label or "",
                    action,
                    resource,
                    profile or "",
                    matched_group or "",
                    base_rule or "",
                    domain_category,
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

    def _canonicalize_path(self, path: str) -> Path:
        """
        Normalize and canonicalize a filesystem path.

        - Expands ~
        - Converts to absolute
        - Resolves .. and symlinks (best-effort)
        """
        p = Path(path).expanduser()
        try:
            # strict=False so missing files still produce a normalized path
            return p.resolve(strict=False)
        except Exception:
            return p.absolute()

    def classify_path(self, path: str, profile: Optional[str] = None) -> BAFClassificationResult:
        """
        Simple semantics:
        - If path falls under any group listed in profile.use_paths, map that group to a risk rule.
        - Currently:
            secrets -> secrets_read
            personal -> personal_read
        - Otherwise: treated as low or high risk depending on whether use_paths is configured.
        """
        use_paths = self._profile_use_paths(profile)
        p = self._canonicalize_path(path)

        matched_group: Optional[str] = None
        matched_root: Optional[str] = None

        # Normalize configured paths to absolute for comparison
        for group_name, cfg in self.paths.items():
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

        # If profile declares use_paths, anything outside those roots is treated as high risk.
        if use_paths and not matched_group:
            return BAFClassificationResult(
                kind="path",
                value=str(p),
                category="L0",
                risk_score=1.0,
                meta={
                    "profile": profile,
                    "matched_group": None,
                    "matched_root": None,
                    "base_rule": None,
                    "score": 100,
                },
            )

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
        return BAFClassificationResult(
            kind="domain",
            value=domain,
            category="unknown",
            risk_score=0.0,
            meta={"profile": profile},
        )

    # === Helpers for domain categorization ===

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

    # === list_dir / read_file / safe_read_file ===

    def list_dir(self, path: str, profile: Optional[str] = None) -> List[str]:
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
            action="list_dir",
            resource=str(self._canonicalize_path(path)),
            profile=profile,
            matched_group=result.meta.get("matched_group"),
            base_rule=result.meta.get("base_rule"),
            score_delta=score_delta,
            decision=decision,
            output_mode="",
        )

        if decision == "block":
            raise PermissionError(f"BAF blocked list_dir on {path} at level {self.state.level}")

        p = self._canonicalize_path(path)
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
            resource=str(self._canonicalize_path(path)),
            profile=profile,
            matched_group=result.meta.get("matched_group"),
            base_rule=result.meta.get("base_rule"),
            score_delta=score_delta,
            decision=decision,
            output_mode="raw",
        )

        if decision == "block":
            raise PermissionError(f"BAF blocked read_file on {path} at level {self.state.level}")

        p = self._canonicalize_path(path)
        return p.read_text(encoding="utf-8", errors="ignore")

    def safe_read_file(self, path: str, profile: Optional[str] = None, mode: Optional[str] = None) -> Any:
        tools_cfg = self.config.raw.get("tools", {})
        file_read_cfg = tools_cfg.get("file_read", {})
        profile_overrides = file_read_cfg.get("profiles", {})

        # Determine effective_mode from explicit arg or config
        if mode is not None:
            effective_mode = mode
        else:
            if profile is not None and profile in profile_overrides:
                eff = profile_overrides[profile]
                if isinstance(eff, dict):
                    effective_mode = eff.get("mode", "raw")
                else:
                    effective_mode = eff
            else:
                if "default_mode" in file_read_cfg:
                    effective_mode = file_read_cfg.get("default_mode", "raw")
                else:
                    default_cfg = file_read_cfg.get("default", {})
                    effective_mode = default_cfg.get("mode", "raw")

        print("DEBUG safe_read_file profile=", profile, "mode_arg=", mode, "effective_mode=", effective_mode)

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

        canonical = self._canonicalize_path(path)

        decision = "allow"
        if self.state.level == "L0" and result.meta.get("matched_group") in ("secrets", "personal"):
            decision = "block"

        self._log_event(
            action="safe_read_file",
            resource=str(canonical),
            profile=profile,
            matched_group=result.meta.get("matched_group"),
            base_rule=result.meta.get("base_rule"),
            score_delta=score_delta,
            decision=decision,
            output_mode=str(effective_mode),
        )

        if decision == "block":
            raise PermissionError(f"BAF blocked safe_read_file on {path} at level {self.state.level}")

        p = canonical
        text = p.read_text(encoding="utf-8", errors="ignore")

        mode_cfg = effective_mode

        if mode_cfg == "metadata":
            stat = p.stat()
            return {
                "mode": "metadata",
                "name": p.name,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "preview": text[:80],
            }

        if mode_cfg == "redacted":
            import re

            redacted = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "[EMAIL]", text)
            redacted = re.sub(r"\b\d{4,}\b", "[NUM]", redacted)
            return {"mode": "redacted", "content": redacted}

        if mode_cfg == "summary":
            return {"mode": "summary", "content": text[:500]}

        return {"mode": "raw", "content": text}

    def http_post(self, url: str, data: str, profile: Optional[str] = None):
        """
        HTTP POST with BAF enforcement and logging.
        """
        import requests

        domain_category = self._categorize_domain(url)
        nbytes = len(data.encode("utf-8", errors="ignore"))

        tools_cfg = self.config.raw.get("tools", {})
        http_cfg = tools_cfg.get("http_post", {})
        http_profiles = http_cfg.get("profiles", {})
        profile_policy = http_profiles.get(profile or "", http_cfg.get("default_action", "allow"))

        # New: basic HTTP limits (payload size + timeout) [web:768][web:752]
        max_bytes = int(http_cfg.get("max_bytes", 1024 * 1024))  # 1 MB default
        timeout_seconds = float(http_cfg.get("timeout_seconds", 5.0))  # 5s default
        if nbytes > max_bytes:
            self._log_event(
                action="http_post",
                resource=url,
                profile=profile,
                matched_group=None,
                base_rule="payload_too_large",
                score_delta=0,
                decision="block",
                output_mode="",
                domain_category=domain_category,
            )
            raise PermissionError(
                f"BAF blocked http_post to {url}: payload too large ({nbytes} bytes > {max_bytes})"
            )

        action_keys: List[str] = []
        if domain_category == "external_unknown":
            action_keys.append("external_http")

        threshold = int(self.risk_rules.get("http_post_large_threshold", 10240))
        if nbytes > threshold:
            action_keys.append("large_http_post")

        score_delta = 0
        for key in action_keys:
            score_delta += compute_risk_delta(key, {"risk_rules": self.risk_rules})

        if score_delta:
            self.state.risk_score = min(100, self.state.risk_score + score_delta)
            update_level(self.state, self.thresholds)

        decision = "allow"

        if profile_policy == "block":
            decision = "block"
        else:
            if self.state.level in {"L1", "L2"} and domain_category == "external_unknown":
                decision = "block"
            if self.state.level == "L0":
                decision = "block"

        print(
            "DEBUG http_post profile:", profile,
            "domain_category:", domain_category
        )

        self._log_event(
            action="http_post",
            resource=url,
            profile=profile,
            matched_group=None,
            base_rule=",".join(action_keys) if action_keys else "",
            score_delta=score_delta,
            decision=decision,
            output_mode="",
            domain_category=domain_category,
        )

        if decision == "block":
            label = self.session_label or "unlabeled"
            raise PermissionError(
                f"BAF blocked http_post to {url} at level {self.state.level} (session_label={label})"
            )

        resp = requests.post(url, data=data, timeout=timeout_seconds)
        return resp
