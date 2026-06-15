"""
recorder.py
-----------
Captures TWO audio streams simultaneously on Windows:
  1. Your microphone (your own voice)
  2. The system "loopback" — i.e. everything playing through your speakers,
     which is the OTHER people on a Zoom/Meet/Teams call.

This is the part that makes the tool actually useful for meetings. It relies on
WASAPI loopback, a Windows feature exposed by the `pyaudiowpatch` library.

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

The recorder still does NO mixing or resampling itself — that happens in
mixer.py after you stop, which is far more robust than syncing two live streams.
"""

import os
import time
import wave
import struct
import threading

import pyaudiowpatch as pyaudio

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


class _StreamRecorder:
    """Records a single input stream straight to a .wav file on disk."""

    def __init__(self, p, device_info, out_path):
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
            # stdlib file I/O and is always safe — only PortAudio's native
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
    Orchestrates recording of mic + system audio at the same time, each streamed
    straight to its own .wav file.

    Usage:
        rec = Recorder(mic_wav_path, sys_wav_path)
        rec.start()
        ... (meeting happens — audio is written to disk continuously) ...
        duration = rec.stop()   # finalises both files, returns seconds recorded
    """

    def __init__(self, mic_path, sys_path):
        self.p = pyaudio.PyAudio()
        self.mic_path = mic_path
        self.sys_path = sys_path
        self.mic_rec = None
        self.sys_rec = None
        self.start_time = None

    def start(self):
        mic_info = self.p.get_default_input_device_info()
        sys_info = _find_loopback_device(self.p)

        self.mic_rec = _StreamRecorder(self.p, mic_info, self.mic_path)
        self.sys_rec = _StreamRecorder(self.p, sys_info, self.sys_path)

        self.start_time = time.time()
        # Start system audio first, then mic — order is not critical because we
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

        The .wav files are finalised by each capture thread's `finally` block, so
        they are complete and valid before we return.
        """
        duration = time.time() - self.start_time if self.start_time else 0
        for r in (self.mic_rec, self.sys_rec):
            r._hard = True
        # Signal stop and wait for each thread to finish writing + finalise its
        # file. If a silent loopback blocks read(), the join times out but the
        # file is still valid up to the last checkpoint (<= CHECKPOINT_SECS old).
        self.mic_rec.stop()
        self.sys_rec.stop()
        return duration

    def close(self):
        self.p.terminate()


def save_wav(path, frames, channels, rate):
    """Helper to write raw int16 frames to a .wav file in one shot (used by
    tools/tests that already have all the frames in memory)."""
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(rate)
        wf.writeframes(frames)
