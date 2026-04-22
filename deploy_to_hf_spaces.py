#!/usr/bin/env python3
"""
Direct deployment to HF Spaces (no git required)
Uploads all necessary files to HF Spaces repository
"""

import os
import sys
from pathlib import Path
import argparse
from huggingface_hub import HfApi


def load_dotenv_defaults() -> dict:
    defaults = {}
    env_path = Path(".env")
    if not env_path.exists():
        return defaults

    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        defaults[key.strip()] = value.strip()
    return defaults


_dotenv_defaults = load_dotenv_defaults()
DEFAULT_SPACE_ID = (
    os.getenv("HF_SPACE_ID")
    or os.getenv("SPACE_REPO_ID")
    or _dotenv_defaults.get("SPACE_REPO_ID")
    or "kunalkachru23/nexus-enhanced-stage"
)


def deploy_to_hf_spaces(space_id=DEFAULT_SPACE_ID, repo_type="space"):
    """
    Deploy NEXUS Enhanced directly to HF Spaces

    Args:
        space_id: HF Spaces ID (default: from .env SPACE_REPO_ID or fallback)
        repo_type: Type of repo (default: "space")
    """

    api = HfApi()

    # Files to upload
    files_to_upload = [
        # Core files
        ("Dockerfile", "Dockerfile"),
        ("start.sh", "start.sh"),
        ("requirements.txt", "requirements.txt"),

        # Server
        ("server/__init__.py", "server/__init__.py"),
        ("server/app.py", "server/app.py"),
        ("server/environment.py", "server/environment.py"),
        ("server/incidents.py", "server/incidents.py"),
        ("server/reward.py", "server/reward.py"),
        ("server/tools.py", "server/tools.py"),
        ("server/agents.py", "server/agents.py"),
        ("server/data_models.py", "server/data_models.py"),
        ("server/difficulty.py", "server/difficulty.py"),
        ("server/static/index.html", "server/static/index.html"),

        # UI
        ("streamlit_app_v2.py", "streamlit_app_v2.py"),

        # Notebooks
        ("notebooks/grpo_colab_v2.ipynb", "notebooks/grpo_colab_v2.ipynb"),

        # Documentation (under docs/)
        ("docs/project/IMPLEMENTATION_SUMMARY.md", "docs/project/IMPLEMENTATION_SUMMARY.md"),
        ("docs/deployment/HF_SPACES_DEPLOYMENT.md", "docs/deployment/HF_SPACES_DEPLOYMENT.md"),
        ("docs/deployment/DEPLOYMENT_CHECKLIST.md", "docs/deployment/DEPLOYMENT_CHECKLIST.md"),
        ("docs/guides/QUICK_START.md", "docs/guides/QUICK_START.md"),
    ]

    print(f"\n🚀 Deploying NEXUS Enhanced to HF Spaces: {space_id}")
    print(f"{'='*70}\n")

    uploaded_count = 0
    failed_files = []

    for local_path, repo_path in files_to_upload:
        full_local_path = Path(local_path)

        if not full_local_path.exists():
            print(f"⚠️  SKIP: {local_path} (not found)")
            continue

        try:
            print(f"📤 Uploading: {repo_path}...", end=" ", flush=True)

            api.upload_file(
                path_or_fileobj=str(full_local_path),
                path_in_repo=repo_path,
                repo_id=space_id,
                repo_type=repo_type,
                commit_message=f"Upload {repo_path}",
            )

            print("✅")
            uploaded_count += 1

        except Exception as e:
            print(f"❌ Error: {e}")
            failed_files.append((repo_path, str(e)))

    print(f"\n{'='*70}")
    print(f"✅ Uploaded: {uploaded_count} files")

    if failed_files:
        print(f"❌ Failed: {len(failed_files)} files")
        for path, error in failed_files:
            print(f"   - {path}: {error}")
        return False

    print(f"\n🎉 Deployment complete!")
    print(f"\nHF Space: https://huggingface.co/spaces/{space_id}")
    print(f"Dashboard: https://{space_id.replace('/', '-')}.hf.space/")
    print(f"\nDocker build will start automatically (5-10 min)")
    print(f"Monitor status: https://huggingface.co/spaces/{space_id}")

    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy NEXUS Enhanced to HF Spaces")
    parser.add_argument(
        "--space-id",
        default=DEFAULT_SPACE_ID,
        help=f"HF Space repo id (default: {DEFAULT_SPACE_ID})",
    )
    args = parser.parse_args()

    # Check if HF token is set
    if not os.getenv("HF_TOKEN"):
        print("❌ Error: HF_TOKEN environment variable not set")
        print("\nSet your HF token:")
        print("  export HF_TOKEN='hf_xxxxxxxxxxxxx'")
        print("\nOr use huggingface-cli:")
        print("  huggingface-cli login")
        sys.exit(1)

    # Deploy
    success = deploy_to_hf_spaces(space_id=args.space_id)
    sys.exit(0 if success else 1)
