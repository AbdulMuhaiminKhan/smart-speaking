"""Errors a pipeline step can raise. Each carries a stable code the UI can explain."""


class PipelineError(Exception):
    """A problem with the user's input that stops the analysis."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class UnsupportedFormatError(PipelineError):
    def __init__(self, detail: str = "") -> None:
        super().__init__(
            "unsupported_format",
            "This file could not be read as a video. Please upload an mp4, webm or mov file."
            + (f" ({detail})" if detail else ""),
        )


class NoAudioError(PipelineError):
    def __init__(self) -> None:
        super().__init__(
            "no_audio",
            "This video has no audio track, so there is no speech to analyze.",
        )


class TooShortError(PipelineError):
    def __init__(self, duration_s: float, min_s: float) -> None:
        super().__init__(
            "too_short",
            f"This clip is {duration_s:.1f} seconds long. Please record at least "
            f"{min_s:.0f} seconds of speech.",
        )


class TooLongError(PipelineError):
    def __init__(self, duration_s: float, max_s: float) -> None:
        super().__init__(
            "too_long",
            f"This clip is {duration_s / 60:.1f} minutes long. The limit is "
            f"{max_s // 60:.0f} minutes.",
        )


class NoSpeechError(PipelineError):
    def __init__(self) -> None:
        super().__init__(
            "no_speech",
            "No speech was detected in this recording. Check that your microphone was on.",
        )
