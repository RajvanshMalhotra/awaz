"""
Speaker identification service — Gaussian distribution model.

Each speaker is represented as a multivariate Gaussian over their embedding space.
Recognition is margin-based: the top speaker must score meaningfully better than
the second-best. No threshold hyperparameter. Gets more accurate with each enrollment.

Decision logic:
  - 1 speaker enrolled  → always matches (no competition)
  - 2+ speakers         → log-likelihood margin must exceed MIN_MARGIN
  - Too close to call   → returns is_new_speaker=True

MIN_MARGIN (3.0) is not a similarity threshold — it's a log-likelihood gap.
It's far less sensitive to environment than cosine thresholds and rarely needs tuning.
"""

from __future__ import annotations

import json
import logging
import asyncio
from pathlib import Path
from typing import Optional
import numpy as np
import torch
import torchaudio
from speechbrain.inference.speaker import SpeakerRecognition

from core.config import get_settings
from core.models import SpeakerProfile, SpeakerRecognitionResult

settings = get_settings()
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

EMBEDDING_DIM = 192

# Log-likelihood margin required to commit to a speaker over alternatives.
# Lower = more permissive (more false positives).
# Higher = more conservative (more unknowns).
# 3.0 is a principled default — equivalent to ~3 nats of information advantage.
# Unlike cosine threshold, this is relative, so mic/environment variation
# affects all speakers equally and doesn't shift the decision boundary.
MIN_MARGIN = 3.0

# SpeechBrain model identifier
ECAPA_MODEL_ID = "speechbrain/spkrec-ecapa-voxceleb"


# ── Speaker store schema ───────────────────────────────────────────────────────
#
# speakers.json structure (v2 — multi-embedding Gaussian model):
#
# {
#   "<speaker_id>": {
#     "speaker_id": "...",
#     "name": "...",
#     "relationship": "friend",
#     "embeddings": [[...192 floats...], [...], ...],   ← all enrollment samples
#     "mean": [...192 floats...],                        ← running mean
#     "var":  [...192 floats...],                        ← running per-dim variance
#     "n": 3,                                            ← sample count
#     "created_at": "..."
#   }
# }
#
# We use a diagonal covariance (per-dim variance) — full 192x192 covariance
# would need ~200+ samples to be well-conditioned and is overkill here.
# Diagonal still captures "this speaker varies a lot on dim 47" which is
# exactly the signal that separates speakers.


class SpeakerService:
    """
    Manages speaker enrollment and identification using a per-speaker
    Gaussian distribution model over ECAPA-TDNN embeddings.
    """

    def __init__(self) -> None:
        self._model: Optional[SpeakerRecognition] = None
        self._store: dict[str, dict] = {}           # speaker_id → raw dict
        self._store_path = Path(settings.voice_store_path)
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_store()

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Load SpeechBrain model. Called once at app startup."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._load_model)
        logger.info("SpeakerService initialized (%d speakers loaded)", len(self._store))

    def _load_model(self) -> None:
        self._model = SpeakerRecognition.from_hparams(
            source=ECAPA_MODEL_ID,
            savedir="pretrained_models/spkrec-ecapa-voxceleb",
        )
        self._model.eval()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def get_embedding(self, audio_bytes: bytes) -> np.ndarray:
        """Extract a 192-d ECAPA embedding from raw audio bytes."""
        await self._ensure_model()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._extract_embedding, audio_bytes)

    async def _ensure_model(self) -> None:
        """Lazy-load the SpeechBrain model on first use."""
        if self._model is None:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._load_model)

    async def identify_speaker(self, audio_bytes: bytes) -> SpeakerRecognitionResult:
        """
        Identify the speaker in audio_bytes against all enrolled speakers.

        Returns SpeakerRecognitionResult with is_new_speaker=True if:
          - no speakers are enrolled, or
          - the log-likelihood margin between top-1 and top-2 is below MIN_MARGIN
        """
        if not self._store:
            # Skip embedding extraction entirely — no speakers to compare against
            return SpeakerRecognitionResult(
                speaker_id=None,
                name="Unknown",
                relationship=None,
                similarity=0.0,
                is_new_speaker=True,
            )

        embedding = await self.get_embedding(audio_bytes)

        scores = self._score_all_speakers(embedding)  # speaker_id → log-likelihood

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_id, best_score = ranked[0]

        # Margin check — only meaningful when there are 2+ speakers
        if len(ranked) >= 2:
            second_score = ranked[1][1]
            margin = best_score - second_score
            if margin < MIN_MARGIN:
                logger.debug(
                    "Speaker ambiguous: margin=%.2f < %.2f (best=%s, second=%s)",
                    margin, MIN_MARGIN, best_id, ranked[1][0],
                )
                return SpeakerRecognitionResult(
                    speaker_id=None,
                    name="Unknown",
                    relationship=None,
                    similarity=round(float(margin / MIN_MARGIN), 4),  # 0–1 confidence proxy
                    is_new_speaker=True,
                )

        speaker = self._store[best_id]

        # Confidence proxy: when only 1 speaker enrolled, margin is undefined —
        # return a fixed indicator. With 2+ speakers, margin/MIN_MARGIN is already
        # clamped to >=1.0 here (we only reach this branch when margin >= MIN_MARGIN).
        if len(ranked) >= 2:
            margin = best_score - ranked[1][1]
            # Normalize: margin of MIN_MARGIN = 0.5, grows toward 1.0 asymptotically
            confidence = round(1.0 - 1.0 / (1.0 + margin / MIN_MARGIN), 4)
        else:
            confidence = 1.0  # only one speaker enrolled, trivially matches

        logger.debug("Identified speaker: %s (confidence=%.3f)", speaker["name"], confidence)

        return SpeakerRecognitionResult(
            speaker_id=best_id,
            name=speaker["name"],
            relationship=speaker.get("relationship"),
            similarity=round(confidence, 4),
            is_new_speaker=False,
        )

    async def enroll_speaker(
        self,
        audio_bytes: bytes,
        name: str,
        relationship: str,
        speaker_id: Optional[str] = None,
    ) -> SpeakerProfile:
        """
        Enroll audio as a new speaker, or add a sample to an existing speaker.

        If speaker_id is provided and exists → adds the embedding to that
        speaker's Gaussian (incremental update, no recompute from scratch).

        If speaker_id is None or not found → creates a new speaker profile.
        """
        embedding = await self.get_embedding(audio_bytes)

        if speaker_id and speaker_id in self._store:
            profile = self._update_speaker(speaker_id, embedding)
            logger.info("Updated speaker '%s' (n=%d samples)", profile["name"], profile["n"])
        else:
            profile = self._create_speaker(embedding, name, relationship)
            logger.info("Enrolled new speaker '%s'", profile["name"])

        self._save_store()
        return self._to_speaker_profile(profile)

    def get_all_speakers(self) -> list[SpeakerProfile]:
        return [self._to_speaker_profile(s) for s in self._store.values()]

    def get_speaker(self, speaker_id: str) -> Optional[SpeakerProfile]:
        if speaker_id not in self._store:
            return None
        return self._to_speaker_profile(self._store[speaker_id])

    # ── Gaussian model internals ───────────────────────────────────────────────

    def _score_all_speakers(self, embedding: np.ndarray) -> dict[str, float]:
        """
        Compute log-likelihood of embedding under each speaker's Gaussian.

        Using diagonal covariance:
          log p(x | μ, σ²) = -0.5 * Σ [ log(σ²_i + ε) + (x_i - μ_i)² / (σ²_i + ε) ]

        The constant term -D/2 * log(2π) cancels in all comparisons so we drop it.
        ε is a small regularizer that prevents division by zero on early samples
        where variance hasn't stabilized — again, not a hyperparameter, just
        numerical safety.
        """
        scores = {}
        eps = 1e-6  # numerical stability only, not tunable

        for sid, speaker in self._store.items():
            mean = np.array(speaker["mean"])
            var = np.array(speaker["var"])

            # Regularized log-likelihood under diagonal Gaussian
            log_var = np.log(var + eps)
            mahal = ((embedding - mean) ** 2) / (var + eps)
            log_likelihood = -0.5 * np.sum(log_var + mahal)

            scores[sid] = float(log_likelihood)

        return scores

    def _create_speaker(
        self, embedding: np.ndarray, name: str, relationship: str
    ) -> dict:
        """Initialize a new speaker profile from the first enrollment sample."""
        import uuid
        from datetime import datetime

        speaker_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        profile = {
            "speaker_id": speaker_id,
            "name": name,
            "relationship": relationship,
            "embeddings": [embedding.tolist()],
            "mean": embedding.tolist(),
            "var": np.zeros(EMBEDDING_DIM).tolist(),  # variance = 0 with 1 sample
            "n": 1,
            "created_at": now,
        }
        self._store[speaker_id] = profile
        return profile

    def _update_speaker(self, speaker_id: str, new_embedding: np.ndarray) -> dict:
        """
        Welford's online algorithm for updating mean and variance incrementally.

        This is numerically stable and requires only the new sample + current stats.
        No need to store or iterate over all past embeddings.
        O(D) time, O(D) space — same as a single embedding.
        """
        profile = self._store[speaker_id]
        n = profile["n"]
        mean = np.array(profile["mean"])
        # M2 is sum of squared deviations — we store variance = M2/n, so recover M2
        M2 = np.array(profile["var"]) * n

        # Welford update
        n_new = n + 1
        delta = new_embedding - mean
        mean_new = mean + delta / n_new
        delta2 = new_embedding - mean_new
        M2_new = M2 + delta * delta2

        profile["n"] = n_new
        profile["mean"] = mean_new.tolist()
        profile["var"] = (M2_new / n_new).tolist()
        profile["embeddings"].append(new_embedding.tolist())  # keep raw for debugging

        self._store[speaker_id] = profile
        return profile

    # ── Embedding extraction ───────────────────────────────────────────────────

    @staticmethod
    def _decode_to_wav(audio_bytes: bytes) -> bytes:
        """
        Transcode any browser audio format (WebM/Opus, MP4/AAC, …) to
        16 kHz mono WAV using ffmpeg. soundfile can then read it natively.
        """
        import subprocess
        result = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-i", "pipe:0",
                "-f", "wav", "-ar", "16000", "-ac", "1",
                "pipe:1",
            ],
            input=audio_bytes,
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg decode failed: {result.stderr.decode()}")
        return result.stdout

    def _extract_embedding(self, audio_bytes: bytes) -> np.ndarray:
        """Decode audio bytes and extract ECAPA-TDNN embedding."""
        import io
        import soundfile as sf

        # Try soundfile directly (works for WAV/FLAC/OGG from test scripts).
        # Browser MediaRecorder sends WebM/Opus which soundfile can't handle —
        # transcode through ffmpeg first in that case.
        try:
            audio_np, sample_rate = sf.read(
                io.BytesIO(audio_bytes), dtype="float32", always_2d=True
            )
        except Exception:
            wav_bytes = self._decode_to_wav(audio_bytes)
            audio_np, sample_rate = sf.read(
                io.BytesIO(wav_bytes), dtype="float32", always_2d=True
            )

        # soundfile returns (frames, channels) — transpose to (channels, frames)
        audio_tensor = torch.from_numpy(audio_np.T)

        # ECAPA expects 16kHz mono (ffmpeg path already normalises; WAV path may not)
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(
                orig_freq=sample_rate, new_freq=16000
            )
            audio_tensor = resampler(audio_tensor)

        # Mix down to mono: (channels, time) → (time,)
        if audio_tensor.shape[0] > 1:
            audio_tensor = audio_tensor.mean(dim=0)
        else:
            audio_tensor = audio_tensor.squeeze(0)

        # encode_batch expects (batch, time)
        audio_tensor = audio_tensor.unsqueeze(0)

        with torch.no_grad():
            embedding = self._model.encode_batch(audio_tensor)

        return embedding.squeeze().numpy()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_store(self) -> None:
        if self._store_path.exists():
            with open(self._store_path, "r") as f:
                self._store = json.load(f)
            # Migrate v1 profiles (single embedding, no Gaussian stats)
            for sid, profile in self._store.items():
                if "mean" not in profile:
                    self._migrate_v1_profile(sid, profile)

    def _save_store(self) -> None:
        with open(self._store_path, "w") as f:
            json.dump(self._store, f, indent=2)

    def _migrate_v1_profile(self, speaker_id: str, profile: dict) -> None:
        """
        Migrate old single-embedding profiles to the Gaussian format.
        Old format had: embedding (list[float])
        New format has: embeddings, mean, var, n
        """
        logger.info("Migrating v1 speaker profile: %s", profile.get("name"))
        old_embedding = np.array(profile.get("embedding", []))

        if old_embedding.size == 0:
            logger.warning("Could not migrate profile %s — no embedding found", speaker_id)
            return

        profile["embeddings"] = [old_embedding.tolist()]
        profile["mean"] = old_embedding.tolist()
        profile["var"] = np.zeros(EMBEDDING_DIM).tolist()
        profile["n"] = 1
        profile.pop("embedding", None)  # remove old field
        self._store[speaker_id] = profile
        self._save_store()

    # ── Schema adapter ────────────────────────────────────────────────────────

    def _to_speaker_profile(self, profile: dict) -> SpeakerProfile:
        """Convert internal store dict to the public SpeakerProfile schema."""
        return SpeakerProfile(
            speaker_id=profile["speaker_id"],
            name=profile["name"],
            relationship=profile.get("relationship", "stranger"),
            # Return mean as the canonical embedding for API compatibility
            embedding=profile["mean"],
            created_at=profile.get("created_at", ""),
        )

    # ── Aliases for test_voice.py ─────────────────────────────────────────────
    # test_voice.py calls .save_speaker(name, audio_bytes, relationship) and
    # .identify(audio_bytes). These thin wrappers keep the test script working
    # without touching it, while the canonical API uses the explicit names above.

    async def save_speaker(
        self,
        name: str,
        audio_bytes: bytes,
        relationship,           # Relationship enum or str
    ) -> SpeakerProfile:
        """Alias for enroll_speaker — matches test_voice.py call signature."""
        rel = relationship.value if hasattr(relationship, "value") else str(relationship)
        return await self.enroll_speaker(audio_bytes=audio_bytes, name=name, relationship=rel)

    async def identify(self, audio_bytes: bytes) -> SpeakerRecognitionResult:
        """Alias for identify_speaker — matches test_voice.py call signature."""
        return await self.identify_speaker(audio_bytes)

    def clear_all(self) -> int:
        """Delete all enrolled speaker profiles. Returns count deleted."""
        count = len(self._store)
        self._store.clear()
        if self._store_path.exists():
            self._store_path.write_text("{}")
        return count


# ── Module-level singleton + factory ──────────────────────────────────────────

_speaker_service: Optional[SpeakerService] = None


def get_speaker_service() -> SpeakerService:
    """
    Return the module-level SpeakerService singleton.

    The model is NOT loaded here — call await service.initialize() once
    at app startup (lifespan) or let the first identify/enroll call trigger
    lazy loading via _ensure_model().
    """
    global _speaker_service
    if _speaker_service is None:
        _speaker_service = SpeakerService()
    return _speaker_service