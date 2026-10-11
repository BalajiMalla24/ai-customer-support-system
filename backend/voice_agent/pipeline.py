import importlib
import os
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class VADResult:
    has_speech: bool
    speech_segments: int
    avg_no_speech_prob: float


@dataclass
class TurnDecision:
    is_end_of_turn: bool
    delay_ms: int
    reason: str


class VoicePipeline:
    """Voice pipeline aligned to: VAD -> Turn Detection -> STT -> Agent -> TTS."""

    def __init__(self, whisper_model: Any):
        self.whisper_model = whisper_model
        self.tts_engine = os.getenv("TTS_ENGINE", "kitten").strip().lower()
        self.kitten_voice = os.getenv("KITTEN_TTS_VOICE", "Jasper")
        self.edge_voice = os.getenv("EDGE_TTS_VOICE", "en-IN-NeerjaNeural")

    def transcribe(self, audio_path: str) -> tuple[str, dict]:
        # Whisper STT stage
        result = self.whisper_model.transcribe(audio_path)
        text = (result.get("text") or "").strip()
        return text, result

    def run_vad(self, whisper_result: dict) -> VADResult:
        # Lightweight VAD approximation using Whisper segment confidence.
        segments = whisper_result.get("segments") or []
        if not segments:
            return VADResult(has_speech=False, speech_segments=0, avg_no_speech_prob=1.0)

        probs = []
        speech_segments = 0
        for seg in segments:
            p = float(seg.get("no_speech_prob", 0.5))
            probs.append(p)
            if p < 0.65:
                speech_segments += 1

        avg = sum(probs) / len(probs) if probs else 1.0
        has_speech = speech_segments > 0
        return VADResult(has_speech=has_speech, speech_segments=speech_segments, avg_no_speech_prob=avg)

    def detect_turn_end(self, transcript: str, vad: VADResult) -> TurnDecision:
        text = (transcript or "").strip()
        if not text:
            return TurnDecision(False, 100, "empty transcript")

        # Hybrid turn detection: semantic EOU + VAD gate with delay timers.
        words = text.split()
        word_count = len(words)
        lower_text = text.lower()

        semantic_eou = (
            text.endswith((".", "?", "!"))
            or lower_text.endswith(("thanks", "thank you", "ok", "okay", "done"))
            or (word_count >= 10)
        )

        # Binary speech classifier approximation from Whisper segment confidence.
        speech_detected = vad.has_speech and vad.speech_segments > 0

        if speech_detected and semantic_eou:
            return TurnDecision(True, 60, "semantic+vad agree")

        if speech_detected and not semantic_eou:
            # Wait briefly to catch trailing words before closing turn.
            return TurnDecision(True, 220, "vad-positive semantic-pending")

        if not speech_detected and semantic_eou:
            # A clean transcript exists but speech confidence is weak.
            return TurnDecision(True, 280, "semantic-only timer")

        return TurnDecision(False, 120, "no reliable end-of-turn")

    async def synthesize(self, text: str, output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        filename = f"response_{uuid.uuid4().hex}.mp3"
        out_path = os.path.join(output_dir, filename)

        # Prefer KittenTTS (local) and fallback to Edge TTS.
        if self.tts_engine == "kitten":
            ok = await self._try_kitten_tts(text, out_path)
            if ok:
                return filename

        edge_tts = importlib.import_module("edge_tts")
        communicate = edge_tts.Communicate(text, self.edge_voice)
        await communicate.save(out_path)
        return filename

    async def _try_kitten_tts(self, text: str, out_path: str) -> bool:
        try:
            import kittentts  # type: ignore

            # Support multiple possible APIs to keep integration resilient.
            if hasattr(kittentts, "synthesize_to_file"):
                maybe = kittentts.synthesize_to_file(text=text, output_path=out_path, voice=self.kitten_voice)
                if maybe is not None and hasattr(maybe, "__await__"):
                    await maybe
                return os.path.exists(out_path)

            if hasattr(kittentts, "KittenTTS"):
                engine = kittentts.KittenTTS()
                if hasattr(engine, "synthesize_to_file"):
                    maybe = engine.synthesize_to_file(text=text, output_path=out_path, voice=self.kitten_voice)
                    if maybe is not None and hasattr(maybe, "__await__"):
                        await maybe
                    return os.path.exists(out_path)

            return False
        except Exception as e:
            print(f"[VOICE] KittenTTS unavailable, fallback to Edge TTS. Reason: {e}")
            return False
