from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


class EnergyVAD:
    """Simple energy-based Voice Activity Detection.

    Detects speech by comparing RMS energy against a threshold.
    Tracks silence duration to detect end-of-utterance.
    """

    def __init__(
        self,
        threshold: float = 0.5,
        silence_duration_ms: int = 800,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
    ) -> None:
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self._silence_frames_needed = int(
            silence_duration_ms / frame_duration_ms
        )
        self._silence_frame_count = 0
        self._is_speaking = False
        self._energy_floor = 0.001
        self._calibrated = False
        self._calibration_frames: list[float] = []
        self._calibration_count = 30  # ~1 second of frames for calibration

    def process_frame(self, frame: bytes) -> str:
        """Process a single audio frame.

        Returns:
            "speech_start" — voice activity just started
            "speech_end"   — silence long enough to mark end of utterance
            "speech"       — ongoing speech
            "silence"      — ongoing silence
        """
        audio = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32768.0
        rms = float(np.sqrt(np.mean(audio ** 2)))

        # Auto-calibrate noise floor from first N frames
        if not self._calibrated:
            self._calibration_frames.append(rms)
            if len(self._calibration_frames) >= self._calibration_count:
                self._energy_floor = np.mean(self._calibration_frames) * 1.5 + 0.001
                self._calibrated = True
                logger.debug("VAD calibrated: noise floor=%.4f", self._energy_floor)
            return "silence"

        # Adaptive threshold relative to noise floor
        is_voice = rms > max(self._energy_floor * (1 + self.threshold), 0.01)

        if is_voice:
            self._silence_frame_count = 0
            if not self._is_speaking:
                self._is_speaking = True
                logger.debug("VAD: speech_start (rms=%.4f)", rms)
                return "speech_start"
            return "speech"
        else:
            if self._is_speaking:
                self._silence_frame_count += 1
                if self._silence_frame_count >= self._silence_frames_needed:
                    self._is_speaking = False
                    self._silence_frame_count = 0
                    logger.debug("VAD: speech_end")
                    return "speech_end"
                return "speech"  # Still within silence tolerance
            return "silence"

    def reset(self) -> None:
        """Reset state for a new utterance."""
        self._silence_frame_count = 0
        self._is_speaking = False
