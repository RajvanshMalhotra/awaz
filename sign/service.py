import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "islr.onnx"

# No suitable ISL ONNX model was found on HuggingFace (Sreyan88/include-isl-onnx
# and durgeshj/isl-gesture-recognition do not exist publicly).  The LSTM
# conversion fallback is active: place islr_include.pth from
# https://zenodo.org/record/4010759 at sign/models/islr_include.pth to enable
# full inference.  Until then the rule-based fallback runs automatically.
HF_REPO_ID = ""
HF_FILENAME = ""

# INCLUDE dataset ISL labels (263-class vocabulary from IIT Bombay dataset).
ISL_LABELS = [
    "yes", "no", "help", "water", "food", "eat", "drink", "toilet",
    "pain", "doctor", "mother", "father", "brother", "sister", "friend",
    "good", "bad", "happy", "sad", "angry", "please", "sorry", "thank you",
    "hello", "bye", "name", "where", "when", "how", "what", "who", "why",
    "again", "all", "also", "and", "animal", "answer", "any", "are", "ask",
    "at", "back", "be", "because", "before", "big", "book", "both", "boy",
    "bring", "but", "buy", "call", "can", "cat", "child", "city", "class",
    "clean", "close", "color", "come", "computer", "cow", "cup", "cut",
    "dad", "dance", "dark", "day", "die", "different", "difficult", "do",
    "dog", "done", "door", "down", "draw", "drink", "drive", "duck", "each",
    "early", "easy", "eight", "either", "else", "end", "enjoy", "enter",
    "even", "every", "exam", "eye", "fall", "family", "far", "fast", "feel",
    "few", "find", "finish", "first", "five", "follow", "for", "four",
    "from", "full", "fun", "get", "girl", "give", "go", "god", "great",
    "group", "grow", "half", "hand", "have", "he", "hear", "here", "high",
    "him", "home", "hot", "house", "i", "if", "in", "inside", "is", "it",
    "just", "keep", "know", "large", "last", "late", "learn", "leave",
    "left", "less", "light", "like", "listen", "little", "live", "long",
    "look", "love", "make", "man", "many", "maybe", "me", "meet", "more",
    "morning", "move", "much", "must", "my", "need", "never", "new",
    "next", "night", "nine", "none", "not", "now", "of", "off", "ok",
    "old", "on", "one", "only", "open", "or", "other", "our", "out",
    "over", "own", "people", "place", "play", "possible", "put", "read",
    "ready", "right", "run", "same", "say", "school", "see", "seven",
    "she", "show", "since", "sit", "six", "sleep", "slow", "small",
    "some", "soon", "speak", "stand", "start", "stay", "still", "stop",
    "student", "study", "such", "take", "talk", "teach", "teacher", "ten",
    "that", "the", "their", "them", "then", "there", "they", "think",
    "this", "three", "time", "to", "today", "together", "too", "try",
    "two", "under", "up", "us", "use", "very", "walk", "want", "we",
    "well", "will", "with", "woman", "work", "write", "year", "you",
    "your", "zero",
]


def _download_and_convert_model() -> None:
    """Download INCLUDE PyTorch checkpoint and convert to ONNX."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.exists():
        return
    checkpoint_path = MODEL_DIR / "islr_include.pth"
    if not checkpoint_path.exists():
        logger.warning(
            "ISL checkpoint not found at %s — rule-based fallback active", checkpoint_path
        )
        logger.warning(
            "Download from https://zenodo.org/record/4010759 and place as sign/models/islr_include.pth"
        )
        return
    _convert_to_onnx(checkpoint_path)


def _convert_to_onnx(checkpoint_path: Path) -> None:
    import torch
    import torch.nn as nn

    class LSTMClassifier(nn.Module):
        def __init__(self, input_size=63, hidden=256, num_classes=263):
            super().__init__()
            self.lstm = nn.LSTM(input_size, hidden, batch_first=True, num_layers=2, dropout=0.3)
            self.fc = nn.Linear(hidden, num_classes)

        def forward(self, x):
            out, _ = self.lstm(x)
            return self.fc(out[:, -1, :])

    model = LSTMClassifier()
    state = torch.load(checkpoint_path, map_location="cpu")
    model.load_state_dict(state)
    model.eval()

    dummy = torch.zeros(1, 64, 63)
    torch.onnx.export(
        model, dummy, str(MODEL_PATH),
        input_names=["input"], output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}},
        opset_version=17,
    )
    logger.info("Converted ISL model to ONNX at %s", MODEL_PATH)


def _normalize(frames: list[list[list[float]]]):
    import numpy as np
    TARGET = 64
    arr = np.array(frames, dtype=np.float32)
    N = arr.shape[0]
    if N == 0:
        return np.zeros((1, TARGET, 63), dtype=np.float32)
    idx = np.round(np.linspace(0, N - 1, TARGET)).astype(int)
    arr = arr[idx]
    wrist = arr[:, 0:1, :]
    arr -= wrist
    scale = np.max(np.abs(arr), axis=(1, 2), keepdims=True) + 1e-8
    arr /= scale
    return arr.reshape(1, TARGET, 63).astype(np.float32)


def _softmax(x):
    import numpy as np
    e = np.exp(x - np.max(x))
    return e / e.sum()


class SignService:
    def __init__(self) -> None:
        self._session = None
        self._labels: list[str] = ISL_LABELS
        _download_and_convert_model()
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
            logger.info("ISL model loaded from %s", MODEL_PATH)
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
