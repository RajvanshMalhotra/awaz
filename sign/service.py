import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "islr.onnx"

# Source: Kazuhito00/hand-gesture-recognition-mediapipe (MIT licence)
# Converted from keypoint_classifier.tflite via tf2onnx.
# Input: (batch, 42) — 21 MediaPipe hand landmarks, x and y only, wrist-relative
# and normalised by the max absolute value across all coordinates.
# Output: (batch, 4) — softmax probabilities over 4 gesture classes.
MODEL_SOURCE = (
    "https://github.com/kinivi/hand-gesture-recognition-mediapipe/raw/main/"
    "model/keypoint_classifier/keypoint_classifier.tflite"
)

# 4-class vocabulary from the keypoint_classifier label CSV.
GESTURE_LABELS = ["Open", "Close", "Pointer", "OK"]


def _normalize(frames: list[list[list[float]]]):
    """Extract a single representative frame and return (1, 42) float32.

    The keypoint classifier operates on one frame at a time, not sequences.
    We pick the middle frame, drop z, make landmarks wrist-relative, then
    normalise by the peak absolute coordinate value.
    """
    import numpy as np
    if not frames:
        return np.zeros((1, 42), dtype=np.float32)
    arr = np.array(frames, dtype=np.float32)   # (N, 21, 3)
    mid = arr[len(arr) // 2]                    # (21, 3)
    xy = mid[:, :2]                             # (21, 2) — drop z
    wrist = xy[0:1, :]
    xy = xy - wrist
    scale = np.max(np.abs(xy)) + 1e-8
    xy = xy / scale
    return xy.reshape(1, 42).astype(np.float32)


def _softmax(x):
    import numpy as np
    e = np.exp(x - np.max(x))
    return e / e.sum()


class SignService:
    def __init__(self) -> None:
        self._session = None
        self._labels: list[str] = GESTURE_LABELS
        self._load()

    def _load(self) -> None:
        if not MODEL_PATH.exists():
            logger.warning("ONNX model not found — rule-based fallback active")
            return
        try:
            import onnxruntime as ort
            self._session = ort.InferenceSession(
                str(MODEL_PATH), providers=["CPUExecutionProvider"]
            )
            logger.info("Gesture model loaded from %s", MODEL_PATH)
        except Exception as e:
            logger.warning("Failed to load ONNX model: %s", e)

    def classify_with_confidence(
        self, landmark_frames: list[list[list[float]]]
    ) -> tuple[str, float]:
        """Returns (label, confidence_score). Score is 0.0 if model not loaded."""
        if not landmark_frames:
            return "", 0.0
        if self._session is None:
            label = self._rule_fallback(landmark_frames)
            return label, 0.5  # rule-based has no real confidence
        try:
            import numpy as np
            x = _normalize(landmark_frames)
            input_name = self._session.get_inputs()[0].name
            outputs = self._session.run(None, {input_name: x})
            logits = outputs[0][0]
            probs = _softmax(logits)
            idx = int(np.argmax(probs))
            score = float(probs[idx])
            label = self._labels[idx] if idx < len(self._labels) else str(idx)
            return label, score
        except Exception as e:
            logger.warning("Inference error: %s", e)
            return self._rule_fallback(landmark_frames), 0.0

    def classify(self, landmark_frames: list[list[list[float]]]) -> str:
        label, _ = self.classify_with_confidence(landmark_frames)
        return label

    def _rule_fallback(self, frames: list[list[list[float]]]) -> str:
        if not frames:
            return ""
        import numpy as np
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
