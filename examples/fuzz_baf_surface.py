# examples/fuzz_baf_surface.py
import os
from baf_core.session import BAFSession, BAFConfig

def main():
    cfg_path = os.getenv("BAF_CONFIG_PATH", "baf_config.dev_laptop.yaml")
    cfg = BAFConfig.from_file(cfg_path)
    sess = BAFSession(cfg, agent_id="fuzz_tester", session_label="fuzz")

    paths = [
        "../../../etc/passwd",
        "/tmp/" + ("x" * 300),
        "./.././../secret.txt",
    ]
    for p in paths:
        try:
            print("FUZZ safe_read_file path=", p)
            sess.safe_read_file(p, profile=os.getenv("BAF_PROFILE", "dev_laptop"), mode="metadata")
        except Exception as e:
            print("  -> ERROR:", repr(e))

    big_payload = "A" * (1024 * 1024 + 10)
    try:
        print("FUZZ http_post big payload")
        sess.http_post("http://127.0.0.1:5000/exfil", big_payload, profile=os.getenv("BAF_PROFILE", "dev_laptop"))
    except Exception as e:
        print("  -> ERROR:", repr(e))

if __name__ == "__main__":
    main()
