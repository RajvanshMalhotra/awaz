import logging
from functools import lru_cache
from pathlib import Path

import numpy as np
import onnxruntime as ort

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "islr.onnx"

# Google ISLR model: hand landmark sequence → one of 250 ASL word classes.
# Substitute with any ONNX model accepting (1, 64, 63) float32 input.
HF_REPO_ID = "flax-sentence-embeddings/asl-signs-onnx"
HF_FILENAME = "model.onnx"

# Full 250-label list from Kaggle ISLR sign_to_prediction_index_map.json.
# Abbreviated fallback used until a full list is wired in.
_FALLBACK_LABELS = [
    "alligator", "any", "bird", "book", "brown", "but", "can",
    "chair", "cloud", "color", "come", "computer", "cow", "cup",
    "dad", "dance", "dark", "dog", "drink", "duck",
]


def _download_model() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.exists():
        return
    logger.info("Downloading ISLR ONNX model from HuggingFace (%s/%s)…", HF_REPO_ID, HF_FILENAME)
    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(repo_id=HF_REPO_ID, filename=HF_FILENAME, local_dir=str(MODEL_DIR))
        Path(path).rename(MODEL_PATH)
        logger.info("Model saved to %s", MODEL_PATH)
    except Exception as e:
        logger.warning("ISLR model download failed: %s — rule-based fallback active", e)


def _normalize(frames: list[list[list[float]]]) -> np.ndarray:
    """Resample to 64 frames and normalize landmarks relative to wrist. Returns (1, 64, 63) float32."""
    TARGET = 64
    arr = np.array(frames, dtype=np.float32)  # (N, 21, 3)
    N = arr.shape[0]
    if N == 0:
        return np.zeros((1, TARGET, 63), dtype=np.float32)

    idx = np.round(np.linspace(0, N - 1, TARGET)).astype(int)
    arr = arr[idx]  # (64, 21, 3)

    wrist = arr[:, 0:1, :]
    arr -= wrist
    scale = np.max(np.abs(arr), axis=(1, 2), keepdims=True) + 1e-8
    arr /= scale

    return arr.reshape(1, TARGET, 63).astype(np.float32)


class SignService:
    def __init__(self) -> None:
        self._session: ort.InferenceSession | None = None
        self._labels: list[str] = _FALLBACK_LABELS
        _download_model()
        self._load()

    def _load(self) -> None:
        if not MODEL_PATH.exists():
            logger.warning("ONNX model not found — rule-based fallback active")
            return
        try:
            self._session = ort.InferenceSession(
                str(MODEL_PATH), providers=["CPUExecutionProvider"]
            )
            logger.info("ISLR model loaded from %s", MODEL_PATH)
        except Exception as e:
            logger.warning("Failed to load ONNX model: %s", e)

    def classify(self, landmark_frames: list[list[list[float]]]) -> str:
        """
        Classify a hand landmark sequence.
        landmark_frames: N frames × 21 landmarks × [x, y, z]
        Returns a word from the ASL vocabulary.
        """
        if not landmark_frames:
            return ""

        if self._session is None:
            return self._rule_fallback(landmark_frames)

        try:
            x = _normalize(landmark_frames)
            input_name = self._session.get_inputs()[0].name
            outputs = self._session.run(None, {input_name: x})
            idx = int(np.argmax(outputs[0]))
            return self._labels[idx] if idx < len(self._labels) else str(idx)
        except Exception as e:
            logger.warning("Inference error: %s", e)
            return self._rule_fallback(landmark_frames)

    def _rule_fallback(self, frames: list[list[list[float]]]) -> str:
        """Count extended fingers from the middle frame and return a gesture label."""
        if not frames:
            return ""
        lms = np.array(frames[len(frames) // 2], dtype=np.float32)
        tips = [4, 8, 12, 16, 20]
        mcps = [2, 5, 9, 13, 17]
        extended = [lms[tip][1] < lms[mcp][1] for tip, mcp in zip(tips, mcps)]
        n = sum(extended)
        if n == 0:
            return "stop"
        if n == 5:
            return "hello"
        if extended[1] and not extended[2]:
            return "one"
        if extended[1] and extended[2] and not extended[3]:
            return "peace"
        if extended[0] and not extended[1]:
            return "good"
        return f"sign({n})"


@lru_cache(maxsize=1)
def get_sign_service() -> SignService:
    return SignService()
