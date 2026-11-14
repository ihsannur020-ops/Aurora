import hashlib
import json
import os
import sys
import urllib.request

OFFICIAL_MANIFEST_URL = "https://host.getaurora.moe/files/app/windows/manifest.json"
GITHUB_USER = "ihsannur020-ops"
GITHUB_REPO = "Aurora"
RELEASE_BASE_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/latest/download/"


def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def main():
    print(f"Fetching official manifest from {OFFICIAL_MANIFEST_URL}...")
    try:
        req = urllib.request.Request(
            OFFICIAL_MANIFEST_URL, headers={"User-Agent": "Aurora-Hybrid-Generator"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            manifest = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Warning: Failed to fetch official manifest ({e}). Reading fallback local manifest...")
        if os.path.exists(".aurora_manifest.json"):
            with open(".aurora_manifest.json", "r", encoding="utf-8") as f:
                manifest = json.load(f)
        else:
            print("Error: No manifest source available.")
            sys.exit(1)

    # Executables to be replaced with custom modified versions
    exe_mapping = {
        "Aurora.exe": [
            "./target/release/Aurora.exe",
            "./target/x86_64-pc-windows-gnu/release/Aurora.exe",
            "./target/x86_64-pc-windows-msvc/release/Aurora.exe",
        ],
        "updater.exe": [
            "./target/release/updater.exe",
            "./target/x86_64-pc-windows-gnu/release/updater.exe",
            "./target/x86_64-pc-windows-msvc/release/updater.exe",
        ],
        "oneclick.exe": [
            "./target/release/oneclick.exe",
            "./target/x86_64-pc-windows-gnu/release/oneclick.exe",
            "./target/x86_64-pc-windows-msvc/release/oneclick.exe",
        ],
        "AuroraUninstaller.exe": [
            "./target/release/AuroraUninstaller.exe",
            "./target/x86_64-pc-windows-gnu/release/AuroraUninstaller.exe",
            "./target/x86_64-pc-windows-msvc/release/AuroraUninstaller.exe",
        ],
    }

    # Format of manifest["files"] can be a list of dicts (remote format) or dict (local format)
    is_list_format = isinstance(manifest.get("files"), list)

    for exe_name, candidate_paths in exe_mapping.items():
        found_path = None
        for p in candidate_paths:
            if os.path.exists(p):
                found_path = p
                break

        if not found_path:
            print(f"Notice: {exe_name} not found in build outputs. Skipping override.")
            continue

        file_hash = sha256_file(found_path)
        print(f"Overriding {exe_name} -> SHA256: {file_hash}")

        if exe_name == "updater.exe":
            manifest["updater_hash"] = file_hash

        if is_list_format:
            found_entry = False
            for entry in manifest["files"]:
                if entry.get("path") == exe_name:
                    entry["sha256"] = file_hash
                    entry["url"] = RELEASE_BASE_URL + exe_name
                    found_entry = True
                    break
            if not found_entry:
                manifest["files"].append({
                    "path": exe_name,
                    "sha256": file_hash,
                    "url": RELEASE_BASE_URL + exe_name,
                })
        else:
            manifest["files"][exe_name] = file_hash

    os.makedirs("windows", exist_ok=True)
    out_path = "windows/manifest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Hybrid manifest successfully generated at: {out_path}")
    print(f"-> Executables point to: {RELEASE_BASE_URL}")
    print("-> Engine files (Bin/nte/...) remain pointing to official upstream server.")


if __name__ == "__main__":
    main()
