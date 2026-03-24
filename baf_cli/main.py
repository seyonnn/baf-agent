# baf_cli/main.py

import argparse
import os
import subprocess
from pathlib import Path
from datetime import datetime

EXAMPLE_CONFIG = """# Example BAF config
paths:
  study:
    - data/Study_Materials
  personal:
    - data/Personal_Docs
  secrets:
    - data/Secrets

domains:
  internal_trusted:
    - "localhost"
    - "127.0.0.1"

risk_rules:
  read_secrets: 40
  read_personal: 30
  external_http: 50
  large_http_post: 40
  http_post_large_threshold: 10240

thresholds:
  L2_to_L1: 40
  L1_to_L0: 80

profiles:
  dev_laptop:
    use_paths: ["study", "personal", "secrets"]
  small_enterprise:
    use_paths: ["study", "personal", "secrets"]

tools:
  file_read:
    default:
      mode: raw
    profiles:
      small_enterprise:
        mode: metadata
  http_post:
    max_bytes: 1048576
    timeout_seconds: 5.0
"""

def cmd_init(args):
    path = Path(args.path)
    if path.exists() and not args.force:
        print(f"[baf] Config file already exists at {path}. Use --force to overwrite.")
        return
    path.write_text(EXAMPLE_CONFIG, encoding="utf-8")
    print(f"[baf] Wrote example config to {path}")

def _latest_log():
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return None
    files = sorted(logs_dir.glob("baf_session_*.csv"))
    return files[-1] if files else None

def cmd_console(args):
    log_path = _latest_log()
    if not log_path:
        print("[baf] No log files found in ./logs")
        return
    print(f"[baf] Showing last {args.lines} lines of {log_path}")
    try:
        # Simple Python tail
        lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in lines[-args.lines:]:
            print(line)
    except Exception as e:
        print(f"[baf] Error reading log file: {e!r}")

def cmd_run(args):
    if not args.agent_cmd:
        print("[baf] Usage: baf run -- <your_agent_command> [args...]")
        return

    # Strip the leading "--" if present
    agent_cmd = args.agent_cmd
    if agent_cmd and agent_cmd[0] == "--":
        agent_cmd = agent_cmd[1:]

    if not agent_cmd:
        print("[baf] Usage: baf run -- <your_agent_command> [args...]")
        return

    config_path = args.config
    profile = args.profile

    env = os.environ.copy()
    env["BAF_CONFIG_PATH"] = config_path
    env["BAF_PROFILE"] = profile

    print(f"[baf] Running command with BAF_CONFIG_PATH={config_path}, BAF_PROFILE={profile}")
    result = subprocess.call(agent_cmd, env=env)
    raise SystemExit(result)

def main():
    parser = argparse.ArgumentParser(prog="baf", description="BAF-Agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_init = subparsers.add_parser("init", help="Generate a starter BAF YAML config")
    p_init.add_argument(
        "-p", "--path",
        default="baf_config.example.yaml",
        help="Path for the generated config file (default: baf_config.example.yaml)",
    )
    p_init.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing config file if present",
    )
    p_init.set_defaults(func=cmd_init)

    p_console = subparsers.add_parser("console", help="Inspect latest BAF session log")
    p_console.add_argument(
        "-n", "--lines",
        type=int,
        default=20,
        help="Number of lines to show from the end of the log (default: 20)",
    )
    p_console.set_defaults(func=cmd_console)

    p_run = subparsers.add_parser("run", help="Run an agent command with BAF env configured")
    p_run.add_argument(
        "--config",
        default="baf_config.dev_laptop.yaml",
        help="BAF config path to set in BAF_CONFIG_PATH (default: baf_config.dev_laptop.yaml)",
    )
    p_run.add_argument(
        "--profile",
        default="dev_laptop",
        help="BAF profile name to set in BAF_PROFILE (default: dev_laptop)",
    )
    p_run.add_argument(
        "agent_cmd",
        nargs=argparse.REMAINDER,
        help="Agent command to run (use -- to separate from baf args)",
    )
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)
