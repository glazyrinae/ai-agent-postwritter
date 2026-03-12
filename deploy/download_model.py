import os
from pathlib import Path

from huggingface_hub import snapshot_download


def download_model() -> None:
    """Download the base model into the mounted /models directory."""

    model_id = os.getenv("MODEL_ID", "MTSAIR/Cotype-Nano-4bit")
    local_dir = os.getenv("MODEL_DIR", "/models/cotype-nano")

    print(f"Downloading model {model_id} into {local_dir}...")
    Path(local_dir).mkdir(parents=True, exist_ok=True)

    try:
        snapshot_download(
            repo_id=model_id,
            local_dir=local_dir,
            local_dir_use_symlinks=False,
            token=os.getenv("HF_TOKEN") or None,
        )
        print(f"Model downloaded successfully into {local_dir}")
    except Exception as exc:
        print(f"Download failed: {exc}")
        raise


if __name__ == "__main__":
    download_model()
