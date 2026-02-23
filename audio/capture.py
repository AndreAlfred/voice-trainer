"""
audio/capture.py — Microphone capture running in a background thread.

The AudioCapture class starts a sounddevice input stream in a background
thread. Each audio callback deposits a numpy array of samples into a
thread-safe queue. The UI thread can call get_chunk() to retrieve samples.

Usage:
    capture = AudioCapture()
    capture.start()
    # ... in UI timer:
    chunk = capture.get_chunk()  # returns None if nothing available
    # ...
    capture.stop()
"""

import queue
import numpy as np
import sounddevice as sd


class AudioCapture:
    """Captures microphone audio in a background thread.

    Audio data is placed into an internal queue as numpy float32 arrays.
    Call get_chunk() from any thread to retrieve a chunk (non-blocking).
    """

    def __init__(self, sample_rate: int = 44100, block_size: int = 1024):
        """Create an AudioCapture instance.

        Args:
            sample_rate: Audio sample rate in Hz. 44100 is CD quality.
            block_size:  Number of samples per callback (~23 ms at 44100 Hz).
        """
        self.sample_rate = sample_rate
        self.block_size = block_size
        self._queue: queue.Queue = queue.Queue(maxsize=50)
        self._stream: sd.InputStream | None = None

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time,
        status: sd.CallbackFlags,
    ) -> None:
        """Called by sounddevice on every audio block.

        This runs in a separate thread managed by sounddevice/PortAudio.
        IMPORTANT: Do NOT call Qt methods from here — only put data into
        the queue. The UI thread reads the queue via a QTimer.

        Args:
            indata: Audio samples, shape (frames, channels), float32.
            frames: Number of frames (same as block_size).
            time:   Timestamps (unused).
            status: Flags indicating overflows or underflows.
        """
        if status:
            print(f"[AudioCapture] Warning: {status}")

        # Take the first channel (mono). Copy because indata is a view.
        mono = indata[:, 0].copy()

        # Drop oldest chunk if queue is full (prevents memory growth if UI is slow)
        try:
            self._queue.put_nowait(mono)
        except queue.Full:
            try:
                self._queue.get_nowait()  # discard oldest
            except queue.Empty:
                pass
            self._queue.put_nowait(mono)

    def start(self) -> None:
        """Open the microphone stream and begin capturing."""
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            channels=1,          # mono
            dtype=np.float32,    # standard float range [-1.0, 1.0]
            callback=self._callback,
        )
        self._stream.start()
        print(f"[AudioCapture] Started — {self.sample_rate} Hz, {self.block_size} samples/block")

    def stop(self) -> None:
        """Stop capturing and release the microphone."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            print("[AudioCapture] Stopped")

    def get_chunk(self) -> np.ndarray | None:
        """Return one chunk of audio samples, or None if the queue is empty.

        Non-blocking. Returns a 1D float32 numpy array of length block_size,
        or None if no new audio has arrived.
        """
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None
