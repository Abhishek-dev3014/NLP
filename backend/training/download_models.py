"""Explicit opt-in download; no user article is transmitted."""

from app.ml.features import ENCODER_PATH


def main():
    from huggingface_hub import snapshot_download

    ENCODER_PATH.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        "sentence-transformers/all-MiniLM-L6-v2",
        revision="1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        local_dir=str(ENCODER_PATH),
        allow_patterns=["*.json", "*.txt", "*.safetensors", "1_Pooling/*"],
        ignore_patterns=["onnx/*", "openvino/*"],
    )
    print(f"Compact encoder saved to {ENCODER_PATH}")


if __name__ == "__main__":
    main()
