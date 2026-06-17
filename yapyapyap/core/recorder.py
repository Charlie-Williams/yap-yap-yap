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
    routes their output through (see the README's macOS setup). If none is
    present we degrade to MIC-ONLY rather than failing.

Crash-safe by design
---------------------
Each stream is written to its .wav file **as it is captured**, never buffered in
memory. Memory therefore stays flat no matter how long the meeting runs (a long
meeting would otherwise grow to gigabytes of RAM and risk crashing), and a
partial recording always survives on disk.

To stay valid even if the process is killed mid-recording, the WAV header (which
records the data length) is re-flushed and fsync'd to disk every few seconds
(a "checkpoint"). A hard crash therefore loses at most CHECKPOINT_SECS of audio,
and the file on disk is always a playable, recoverable .wav.

The recorder still does NO mixing or resampling itself - that happens in
mixer.py after you stop, which is far more robust than syncing two live streams.
Keeping this module's public surface identical across platforms (`Recorder`,
`save_wav`) means the worker and the rest of the app never need to know which OS
they're on.
"""

import os
import sys
import time
import wave
import struct
import logging
import threading

IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

_log = logging.getLogger("YapYapYap")

# How often (seconds) to flush + fsync each stream's header to disk. This is the
# maximum amount of audio a hard crash / power loss can cost you.
CHECKPOINT_SECS = 3.0


class _WavStream:
    """A 16-bit PCM .wav file written incrementally.

    The 44-byte canonical WAV header records the data length, which is only
    known once writing finishes. Rather than buffer everything and write the
    header last, we write the header up front and **re-write it** (with the
    current length) on every checkpoint and on close. The file is therefore a
    valid .wav at every checkpoint, so an abrupt kill still leaves a readable,
    recoverable recording.
    """

    def __init__(self, path, channels, rate, sampwidth=2):
        self.path = path
        self.channels = channels
        self.rate = rate
        self.sampwidth = sampwidth
        self._data_len = 0
        self._f = open(path, "wb")
        self._write_header()  # placeholder sizes (data_len == 0)

    def _write_header(self):
        """(Re)write the 44-byte header from offset 0, then return to EOF."""
        byte_rate = self.rate * self.channels * self.sampwidth
        block_align = self.channels * self.sampwidth
        header = b"RIFF" + struct.pack("<I", 36 + self._data_len) + b"WAVE"
        header += b"fmt " + struct.pack(
            "<IHHIIHH", 16, 1, self.channels, self.rate,
            byte_rate, block_align, self.sampwidth * 8)
        header += b"data" + struct.pack("<I", self._data_len)
        self._f.seek(0)
        self._f.write(header)
        self._f.seek(0, os.SEEK_END)  # back to the end, ready to append

    def append(self, frames):
        self._f.write(frames)
        self._data_len += len(frames)

    def checkpoint(self):
        """Flush buffered data and patch the header so the file is valid + on
        disk. Costs at most a few ms; called every CHECKPOINT_SECS."""
        self._f.flush()
        self._write_header()
        self._f.flush()
        try:
            os.fsync(self._f.fileno())
        except OSError:
            pass

    def close(self):
        try:
            self.checkpoint()
        finally:
            self._f.close()


def _write_empty_wav(path, channels=1, rate=16000):
    """Create a valid, empty .wav (used as the system stream in mic-only mode so
    downstream mixing always finds a file to read)."""
    _WavStream(path, channels, rate).close()


# ===========================================================================
# Windows backend - WASAPI loopback via pyaudiowpatch
# ===========================================================================
class _WinStreamRecorder:
    """Records a single WASAPI input stream straight to a .wav file on disk."""

    def __init__(self, pyaudio, p, device_info, out_path):
        self._pyaudio = pyaudio
        self.p = p
        self.device_info = device_info
        self.out_path = out_path
        self.rate = int(device_info["defaultSampleRate"])
        self.channels = int(device_info["maxInputChannels"])
        self.index = device_info["index"]
        self._stop = threading.Event()
        self._hard = False  # when True, skip the native stream teardown
        self._thread = None

    def _run(self):
        pyaudio = self._pyaudio
        wav = _WavStream(self.out_path, self.channels, self.rate)
        last_ckpt = time.time()
        stream = self.p.open(
            format=pyaudio.paInt16,
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
                wav.append(data)
                now = time.time()
                if now - last_ckpt >= CHECKPOINT_SECS:
                    wav.checkpoint()
                    last_ckpt = now
        finally:
            # Finalise the file (writes the final, correct header). This is plain
            # stdlib file I/O and is always safe - only PortAudio's native
            # teardown can segfault a WASAPI-loopback process, so that is what we
            # skip in "hard" mode below.
            wav.close()
            if not self._hard:
                stream.stop_stream()
                stream.close()

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, timeout=2):
        self._stop.set()
        if self._thread is not None:
            # When audio is flowing the read loop exits within one ~20 ms buffer;
            # a silent WASAPI loopback can briefly block in read(), so we cap the
            # wait rather than stalling teardown. Even if it times out, the file
            # is valid up to the last checkpoint.
            self._thread.join(timeout=timeout)


def _find_wasapi_loopback_device(pyaudio, p):
    """Return the WASAPI loopback device matching the default speakers."""
    wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

    # If the default output isn't already a loopback device, find its
    # loopback twin (pyaudiowpatch exposes one per output device).
    if not default_speakers.get("isLoopbackDevice", False):
        for loopback in p.get_loopback_device_info_generator():
            if default_speakers["name"] in loopback["name"]:
                return loopback
        raise RuntimeError(
            "Could not find a loopback device for your default speakers. "
            "Make sure audio output is set to a normal device."
        )
    return default_speakers


class _WindowsRecorder:
    """Records mic + WASAPI-loopback system audio on Windows, each to disk."""

    def __init__(self, mic_path, sys_path):
        import pyaudiowpatch as pyaudio  # imported lazily: Windows-only wheel
        self._pyaudio = pyaudio
        self.p = pyaudio.PyAudio()
        self.mic_path = mic_path
        self.sys_path = sys_path
        self.mic_rec = None
        self.sys_rec = None
        self.start_time = None

    def start(self):
        mic_info = self.p.get_default_input_device_info()
        sys_info = _find_wasapi_loopback_device(self._pyaudio, self.p)

        self.mic_rec = _WinStreamRecorder(self._pyaudio, self.p, mic_info,
                                          self.mic_path)
        self.sys_rec = _WinStreamRecorder(self._pyaudio, self.p, sys_info,
                                          self.sys_path)

        self.start_time = time.time()
        # Start system audio first, then mic - order is not critical because we
        # align lengths later, but starting close together minimises drift.
        self.sys_rec.start()
        self.mic_rec.start()

    def stop(self):
        """Graceful stop with full native teardown. Returns the duration."""
        duration = time.time() - self.start_time if self.start_time else 0
        self.mic_rec.stop()
        self.sys_rec.stop()
        return duration

    def stop_hard(self):
        """
        Stop recording WITHOUT any native PortAudio teardown, then finalise both
        .wav files. Intended for recorder_worker.py, which hard-exits immediately
        afterwards: skipping stream.close()/Pa_Terminate avoids the native
        segfault those calls can trigger in a process that opened a WASAPI
        loopback stream. The OS releases the device on process exit.
        """
        duration = time.time() - self.start_time if self.start_time else 0
        for r in (self.mic_rec, self.sys_rec):
            r._hard = True
        self.mic_rec.stop()
        self.sys_rec.stop()
        return duration

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


class _MacStreamRecorder:
    """Records a single sounddevice input stream straight to a .wav on disk."""

    def __init__(self, sd, device_index, rate, channels, out_path):
        self._sd = sd
        self.index = device_index
        self.rate = int(rate)
        self.channels = int(channels)
        self.out_path = out_path
        self._wav = None
        self._stream = None
        self._last_ckpt = 0.0
        self._lock = threading.Lock()

    def _callback(self, indata, frame_count, time_info, status):
        # indata is a raw buffer (RawInputStream, dtype int16); store the
        # interleaved int16 bytes - exactly what stdlib `wave` and mixer.py want.
        with self._lock:
            if self._wav is None:
                return
            self._wav.append(bytes(indata))
            now = time.time()
            if now - self._last_ckpt >= CHECKPOINT_SECS:
                self._wav.checkpoint()
                self._last_ckpt = now

    def start(self):
        self._wav = _WavStream(self.out_path, self.channels, self.rate)
        self._last_ckpt = time.time()
        self._stream = self._sd.RawInputStream(
            samplerate=self.rate,
            device=self.index,
            channels=self.channels,
            dtype="int16",
            blocksize=1024,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self, timeout=2):
        # CoreAudio has no WASAPI-style teardown segfault, so a clean stop is
        # always safe here (the _hard distinction matters only on Windows).
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        with self._lock:
            if self._wav is not None:
                self._wav.close()
                self._wav = None


class _MacRecorder:
    """Records mic + virtual-loopback system audio on macOS via sounddevice."""

    def __init__(self, mic_path, sys_path):
        import sounddevice as sd  # lazy: not needed on non-mac imports
        self._sd = sd
        self.mic_path = mic_path
        self.sys_path = sys_path
        self.mic_rec = None
        self.sys_rec = None
        self.start_time = None

    def _default_input_index(self):
        for idx, dev in enumerate(self._sd.query_devices()):
            if dev.get("max_input_channels", 0) >= 1:
                return idx
        raise RuntimeError("No microphone (audio input device) found.")

    def _find_loopback_device(self):
        """Find a virtual audio device that carries system audio as an input."""
        sd = self._sd
        override = os.environ.get("YAPYAPYAP_LOOPBACK_DEVICE", "").strip().lower()
        names = (override,) if override else _MAC_LOOPBACK_NAMES

        for idx, dev in enumerate(sd.query_devices()):
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
        self.mic_rec = _MacStreamRecorder(sd, mic_index, mic_rate, mic_ch,
                                          self.mic_path)

        # System audio needs a virtual loopback device (BlackHole). If none is
        # present, degrade gracefully to MIC-ONLY rather than failing outright:
        # an in-person meeting (laptop mic in the room) is captured fully; remote
        # call audio won't be until the user sets up a loopback device.
        try:
            sys_index, sys_dev = self._find_loopback_device()
            sys_rate = int(sys_dev["default_samplerate"])
            sys_ch = max(1, int(sys_dev["max_input_channels"]))
            self.sys_rec = _MacStreamRecorder(sd, sys_index, sys_rate, sys_ch,
                                              self.sys_path)
        except RuntimeError as e:
            _log.warning("Recording mic only (no system-audio device): %s", e)
            self.sys_rec = None
            _write_empty_wav(self.sys_path)  # keep downstream happy

        self.start_time = time.time()
        if self.sys_rec is not None:
            self.sys_rec.start()
        self.mic_rec.start()

    def stop(self):
        duration = time.time() - self.start_time if self.start_time else 0
        self.mic_rec.stop()
        if self.sys_rec is not None:
            self.sys_rec.stop()
        return duration

    def stop_hard(self):
        # CoreAudio: a clean stop is safe, so this is the same as stop(). Kept as
        # a separate method so recorder_worker.py stays platform-agnostic.
        return self.stop()

    def close(self):
        pass  # sounddevice manages PortAudio's lifetime itself


# ===========================================================================
# Platform dispatch + shared helpers
# ===========================================================================
def Recorder(mic_path, sys_path):
    """Return a platform-appropriate recorder that streams mic + system audio
    straight to `mic_path` / `sys_path`.

    Kept as a factory (callable like the old class) so existing call sites -
    `recorder.Recorder(mic, sys)` - work unchanged across platforms.
    """
    if IS_WINDOWS:
        return _WindowsRecorder(mic_path, sys_path)
    if IS_MAC:
        return _MacRecorder(mic_path, sys_path)
    raise RuntimeError(
        "Audio recording is only supported on Windows and macOS on this build.")


def save_wav(path, frames, channels, rate):
    """Helper to write raw int16 frames to a .wav file in one shot (used by
    tools/tests that already have all the frames in memory)."""
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(rate)
        wf.writeframes(frames)
