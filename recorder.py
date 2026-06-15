"""
recorder.py
-----------
Captures TWO audio streams simultaneously on Windows:
  1. Your microphone (your own voice)
  2. The system "loopback" — i.e. everything playing through your speakers,
     which is the OTHER people on a Zoom/Meet/Teams call.

This is the part that makes the tool actually useful for meetings. It relies on
WASAPI loopback, a Windows feature exposed by the `pyaudiowpatch` library.

The recorder just COLLECTS raw audio frames while recording. It does no mixing
or resampling itself — that happens in mixer.py after you stop, which is far
more robust than trying to sync two live streams in real time.
"""

import threading
import wave
import time

import pyaudiowpatch as pyaudio


class _StreamRecorder:
    """Records a single input stream into an in-memory list of frames."""

    def __init__(self, p, device_info):
        self.p = p
        self.device_info = device_info
        self.rate = int(device_info["defaultSampleRate"])
        self.channels = int(device_info["maxInputChannels"])
        self.index = device_info["index"]
        self.frames = []
        self._stop = threading.Event()
        self._hard = False  # when True, skip the native stream teardown
        self._thread = None

    def _run(self):
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
                self.frames.append(data)
        finally:
            # In "hard" mode we deliberately do NOT close the stream: PortAudio's
            # native teardown is the call that can segfault a process that has
            # used WASAPI loopback. The worker hard-exits right after grabbing
            # the frames, so the OS reclaims the audio device anyway.
            if not self._hard:
                stream.stop_stream()
                stream.close()

    def start(self):
        self._stop.clear()
        self.frames = []
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            # When audio is flowing, the read loop exits within one ~20 ms
            # buffer. A silent WASAPI loopback can briefly block in read(), so
            # we cap the wait at 2 s rather than stalling teardown.
            self._thread.join(timeout=2)


def _find_loopback_device(p):
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


class Recorder:
    """
    Orchestrates recording of mic + system audio at the same time.

    Usage:
        rec = Recorder()
        rec.start()
        ... (meeting happens) ...
        result = rec.stop()   # dict with frames + format info for both streams
    """

    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.mic_rec = None
        self.sys_rec = None
        self.start_time = None

    def start(self):
        mic_info = self.p.get_default_input_device_info()
        sys_info = _find_loopback_device(self.p)

        self.mic_rec = _StreamRecorder(self.p, mic_info)
        self.sys_rec = _StreamRecorder(self.p, sys_info)

        self.start_time = time.time()
        # Start system audio first, then mic — order is not critical because we
        # align lengths later, but starting close together minimises drift.
        self.sys_rec.start()
        self.mic_rec.start()

    def stop(self):
        # Capture the true recording length now, BEFORE stopping the streams,
        # so the figure isn't inflated by stream-teardown time.
        duration = time.time() - self.start_time if self.start_time else 0
        self.mic_rec.stop()
        self.sys_rec.stop()
        return self._collect(duration)

    def stop_hard(self):
        """
        Stop recording WITHOUT any native PortAudio teardown and return the
        captured frames. Intended for recorder_worker.py, which hard-exits
        immediately afterwards: skipping stream.close()/Pa_Terminate avoids the
        native segfault those calls can trigger in a process that opened a
        WASAPI loopback stream. The OS releases the device on process exit.
        """
        duration = time.time() - self.start_time if self.start_time else 0
        for r in (self.mic_rec, self.sys_rec):
            r._hard = True
            r._stop.set()
        # Give the read loops a moment to stop appending frames cleanly.
        time.sleep(0.25)
        return self._collect(duration)

    def _collect(self, duration):
        return {
            "mic": {
                "frames": b"".join(self.mic_rec.frames),
                "rate": self.mic_rec.rate,
                "channels": self.mic_rec.channels,
            },
            "sys": {
                "frames": b"".join(self.sys_rec.frames),
                "rate": self.sys_rec.rate,
                "channels": self.sys_rec.channels,
            },
            "duration": duration,
        }

    def close(self):
        self.p.terminate()


def save_wav(path, frames, channels, rate):
    """Helper to write raw int16 frames to a .wav file (for archiving)."""
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(rate)
        wf.writeframes(frames)
