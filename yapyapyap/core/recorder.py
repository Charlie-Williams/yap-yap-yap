"""
recorder.py
-----------
Captures TWO audio streams simultaneously:
  1. Your microphone (your own voice)
  2. The system "loopback" - i.e. everything playing through your speakers,
     which is the OTHER people on a Zoom/Meet/Teams call.

This is the part that makes the tool actually useful for meetings. How the
loopback is captured is platform-specific:

  * Windows - WASAPI loopback, exposed by the `pyaudiowpatch` library. The
    default speakers have a matching "loopback" input device we record from.
  * macOS   - there is no built-in loopback. We capture system audio from a
    virtual audio device (BlackHole, Loopback, Soundflower, ...) that the user
    routes their output through. See the README's macOS setup section.

Either way the recorder just COLLECTS raw int16 frames while recording and
hands back, per stream, a `{frames, rate, channels}` dict. It does no mixing or
resampling itself - that happens in mixer.py after you stop, which is far more
robust than trying to sync two live streams in real time. Keeping this module's
public surface identical across platforms (`Recorder`, `save_wav`) means the
worker and the rest of the app never need to know which OS they're on.
"""

import sys
import wave
import logging

IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

_log = logging.getLogger("YapYapYap")


# ===========================================================================
# Windows backend - WASAPI loopback via pyaudiowpatch
# ===========================================================================
class _WindowsRecorder:
    """Records mic + WASAPI-loopback system audio on Windows."""

    def __init__(self):
        import pyaudiowpatch as pyaudio  # imported lazily: Windows-only wheel
        self._pyaudio = pyaudio
        self.p = pyaudio.PyAudio()
        self.mic_rec = None
        self.sys_rec = None
        self.start_time = None

    class _StreamRecorder:
        """Records a single input stream into an in-memory list of frames."""

        def __init__(self, pyaudio, p, device_info):
            self._pyaudio = pyaudio
            self.p = p
            self.device_info = device_info
            self.rate = int(device_info["defaultSampleRate"])
            self.channels = int(device_info["maxInputChannels"])
            self.index = device_info["index"]
            self.frames = []
            self._stop = __import__("threading").Event()
            self._hard = False  # when True, skip the native stream teardown
            self._thread = None

        def _run(self):
            stream = self.p.open(
                format=self._pyaudio.paInt16,
                channels=self.channels,
                rate=self.rate,
                frames_per_buffer=1024,
                input=True,
                input_device_index=self.index,
            )
            try:
                while not self._stop.is_set():
                    # exception_on_overflow=False keeps us going if the buffer
                    # briefly overruns rather than crashing the recording.
                    data = stream.read(1024, exception_on_overflow=False)
                    self.frames.append(data)
            finally:
                # In "hard" mode we deliberately do NOT close the stream:
                # PortAudio's native teardown is the call that can segfault a
                # process that has used WASAPI loopback. The worker hard-exits
                # right after grabbing the frames, so the OS reclaims the device.
                if not self._hard:
                    stream.stop_stream()
                    stream.close()

        def start(self):
            import threading
            self._stop.clear()
            self.frames = []
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

        def stop(self):
            self._stop.set()
            if self._thread is not None:
                # When audio is flowing, the read loop exits within one ~20 ms
                # buffer. A silent WASAPI loopback can briefly block in read(),
                # so we cap the wait at 2 s rather than stalling teardown.
                self._thread.join(timeout=2)

    def _find_loopback_device(self):
        """Return the WASAPI loopback device matching the default speakers."""
        pyaudio = self._pyaudio
        wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = self.p.get_device_info_by_index(
            wasapi_info["defaultOutputDevice"])

        # If the default output isn't already a loopback device, find its
        # loopback twin (pyaudiowpatch exposes one per output device).
        if not default_speakers.get("isLoopbackDevice", False):
            for loopback in self.p.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    return loopback
            raise RuntimeError(
                "Could not find a loopback device for your default speakers. "
                "Make sure audio output is set to a normal device."
            )
        return default_speakers

    def start(self):
        mic_info = self.p.get_default_input_device_info()
        sys_info = self._find_loopback_device()

        self.mic_rec = self._StreamRecorder(self._pyaudio, self.p, mic_info)
        self.sys_rec = self._StreamRecorder(self._pyaudio, self.p, sys_info)

        import time
        self.start_time = time.time()
        # Start system audio first, then mic - order is not critical because we
        # align lengths later, but starting close together minimises drift.
        self.sys_rec.start()
        self.mic_rec.start()

    def stop(self):
        import time
        # Capture the true recording length now, BEFORE stopping the streams,
        # so the figure isn't inflated by stream-teardown time.
        duration = time.time() - self.start_time if self.start_time else 0
        self.mic_rec.stop()
        self.sys_rec.stop()
        return _collect(self.mic_rec, self.sys_rec, duration)

    def stop_hard(self):
        """
        Stop recording WITHOUT any native PortAudio teardown and return the
        captured frames. Intended for recorder_worker.py, which hard-exits
        immediately afterwards: skipping stream.close()/Pa_Terminate avoids the
        native segfault those calls can trigger in a process that opened a
        WASAPI loopback stream. The OS releases the device on process exit.
        """
        import time
        duration = time.time() - self.start_time if self.start_time else 0
        for r in (self.mic_rec, self.sys_rec):
            r._hard = True
            r._stop.set()
        # Give the read loops a moment to stop appending frames cleanly.
        time.sleep(0.25)
        return _collect(self.mic_rec, self.sys_rec, duration)

    def close(self):
        self.p.terminate()


# ===========================================================================
# macOS backend - mic + virtual loopback device via sounddevice (PortAudio)
# ===========================================================================
# Names of common macOS virtual audio devices that expose system audio as an
# input. The user routes their output through one of these (see README); we
# record system audio from its input side. Matched case-insensitively as a
# substring of the device name. Override with $YAPYAPYAP_LOOPBACK_DEVICE.
_MAC_LOOPBACK_NAMES = ("blackhole", "loopback", "soundflower", "aggregate")


class _MacRecorder:
    """Records mic + virtual-loopback system audio on macOS via sounddevice."""

    def __init__(self):
        import sounddevice as sd  # imported lazily so non-mac imports don't need it
        self._sd = sd
        self.mic_rec = None
        self.sys_rec = None
        self.start_time = None

    class _StreamRecorder:
        """Records a single sounddevice input stream into raw int16 frames."""

        def __init__(self, sd, device_index, rate, channels):
            self._sd = sd
            self.index = device_index
            self.rate = int(rate)
            self.channels = int(channels)
            self.frames = []
            self._stream = None
            self._hard = False

        def _callback(self, indata, frame_count, time_info, status):
            # indata is an (frames, channels) int16 ndarray; store interleaved
            # int16 bytes - exactly what stdlib `wave` and mixer.py expect.
            self.frames.append(bytes(indata))

        def start(self):
            self.frames = []
            self._stream = self._sd.RawInputStream(
                samplerate=self.rate,
                device=self.index,
                channels=self.channels,
                dtype="int16",
                blocksize=1024,
                callback=self._callback,
            )
            self._stream.start()

        def stop(self):
            if self._stream is not None:
                if not self._hard:
                    self._stream.stop()
                    self._stream.close()
                self._stream = None

    def _find_loopback_device(self):
        """Find a virtual audio device that carries system audio as an input."""
        import os
        sd = self._sd
        devices = sd.query_devices()

        override = os.environ.get("YAPYAPYAP_LOOPBACK_DEVICE", "").strip().lower()
        names = (override,) if override else _MAC_LOOPBACK_NAMES

        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) < 1:
                continue
            name = dev.get("name", "").lower()
            if any(token in name for token in names if token):
                return idx, dev

        raise RuntimeError(
            "Could not find a system-audio (loopback) input device. Install a "
            "virtual audio device such as BlackHole (https://existential.audio/"
            "blackhole/) and route your output through it - see the README's "
            "macOS setup. Set $YAPYAPYAP_LOOPBACK_DEVICE to its name to override."
        )

    def start(self):
        sd = self._sd

        mic_index = sd.default.device[0]
        if mic_index is None or mic_index < 0:
            mic_index = self._default_input_index()
        mic_dev = sd.query_devices(mic_index)
        mic_rate = int(mic_dev["default_samplerate"])
        mic_ch = max(1, int(mic_dev["max_input_channels"]))

        self.mic_rec = self._StreamRecorder(sd, mic_index, mic_rate, mic_ch)

        # System audio needs a virtual loopback device (BlackHole). If none is
        # present, degrade gracefully to MIC-ONLY rather than failing outright:
        # the user can still record their own voice and anyone in the room
        # (an in-person meeting works fully). Remote call audio won't be
        # captured until they set up a loopback device - see the README.
        try:
            sys_index, sys_dev = self._find_loopback_device()
            sys_rate = int(sys_dev["default_samplerate"])
            sys_ch = max(1, int(sys_dev["max_input_channels"]))
            self.sys_rec = self._StreamRecorder(sd, sys_index, sys_rate, sys_ch)
        except RuntimeError as e:
            _log.warning("Recording mic only (no system-audio device): %s", e)
            self.sys_rec = None

        import time
        self.start_time = time.time()
        if self.sys_rec is not None:
            self.sys_rec.start()
        self.mic_rec.start()

    def _default_input_index(self):
        sd = self._sd
        for idx, dev in enumerate(sd.query_devices()):
            if dev.get("max_input_channels", 0) >= 1:
                return idx
        raise RuntimeError("No microphone (audio input device) found.")

    def stop(self):
        import time
        duration = time.time() - self.start_time if self.start_time else 0
        self.mic_rec.stop()
        if self.sys_rec is not None:
            self.sys_rec.stop()
        return _collect(self.mic_rec, self.sys_rec, duration)

    def stop_hard(self):
        # macOS/PortAudio (CoreAudio) has no WASAPI-style teardown segfault, so
        # a clean stop is safe here. We keep the same method name/signature as
        # the Windows backend so recorder_worker.py is platform-agnostic.
        return self.stop()

    def close(self):
        pass  # sounddevice manages PortAudio's lifetime itself


# ===========================================================================
# Shared helpers + platform dispatch
# ===========================================================================
def _collect(mic_rec, sys_rec, duration):
    def pack(rec):
        # A None stream (e.g. mic-only on macOS with no loopback device) becomes
        # a valid empty/silent stream; mixer.py pads it to match the other side.
        if rec is None:
            return {"frames": b"", "rate": 16000, "channels": 1}
        return {
            "frames": b"".join(rec.frames),
            "rate": rec.rate,
            "channels": rec.channels,
        }
    return {"mic": pack(mic_rec), "sys": pack(sys_rec), "duration": duration}


def Recorder():
    """Return a platform-appropriate recorder.

    Kept as a factory (callable like the old class) so existing call sites -
    `recorder.Recorder()` - work unchanged across platforms.
    """
    if IS_WINDOWS:
        return _WindowsRecorder()
    if IS_MAC:
        return _MacRecorder()
    raise RuntimeError(
        "Audio recording is only supported on Windows and macOS on this build.")


def save_wav(path, frames, channels, rate):
    """Helper to write raw int16 frames to a .wav file (for archiving)."""
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(rate)
        wf.writeframes(frames)
