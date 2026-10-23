"""Local text-to-speech through Windows' System.Speech (no network, no key).

Installed voices on the factory machine (2026-10-23): Microsoft Zira Desktop
(en-US), Hortense/Julie/Paul (fr-FR). There is no Arabic voice. The licence
for using these voices in published videos is an open question (see
VIDEO_FACTORY_RIGHTS_AND_POLICY_CHECKLIST.md): renders using them are for
internal review until that is settled.
"""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path

DEFAULT_VOICE = "Microsoft Zira Desktop"

_PS = r"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice($env:GF_TTS_VOICE)
$s.Rate = [int]$env:GF_TTS_RATE
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(22050, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$s.SetOutputToWaveFile($env:GF_TTS_OUT, $fmt)
$s.Speak([IO.File]::ReadAllText($env:GF_TTS_TEXT, [Text.Encoding]::UTF8))
$s.Dispose()
"""


class TTSError(RuntimeError):
    pass


def installed_voices() -> list:
    ps = ("Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer)"
          ".GetInstalledVoices() | % { $_.VoiceInfo.Name + '|' + $_.VoiceInfo.Culture }")
    p = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=60)
    return [tuple(l.split("|", 1)) for l in p.stdout.splitlines() if "|" in l]


def wav_duration(path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def trim_silence(path, threshold_db: float = -45.0, keep_s: float = 0.04) -> float:
    """Cut leading/trailing silence in place; returns the new duration.

    System.Speech pads each utterance (measured 2026-10-23: ~0.1 s before,
    ~0.75 s after). Left in, subtitle cues ran ~0.75 s past the speech."""
    import array
    with wave.open(str(path), "rb") as w:
        params, raw = w.getparams(), w.readframes(w.getnframes())
    if params.sampwidth != 2:
        return wav_duration(path)
    samples = array.array("h", raw)
    ch, rate = params.nchannels, params.framerate
    limit = 32768 * 10 ** (threshold_db / 20)
    win = max(1, rate // 100) * ch  # 10 ms windows
    loud = [i for i in range(0, len(samples), win) if max((abs(x) for x in samples[i:i + win]), default=0) > limit]
    if not loud:
        return wav_duration(path)
    pad = int(keep_s * rate) * ch
    a, b = max(0, loud[0] - pad), min(len(samples), loud[-1] + win + pad)
    a -= a % ch
    b -= b % ch
    with wave.open(str(path), "wb") as w:
        w.setparams(params)
        w.writeframes(samples[a:b].tobytes())
    return (b - a) / ch / rate


def synthesize(text: str, out_wav, voice: str = DEFAULT_VOICE, rate: int = 0, timeout: int = 120) -> float:
    """Speak `text` into `out_wav` (22.05 kHz, 16-bit, mono). Returns seconds."""
    import os
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    txt = out_wav.with_suffix(".txt")
    txt.write_text(text, encoding="utf-8")
    env = dict(os.environ, GF_TTS_VOICE=voice, GF_TTS_RATE=str(int(rate)), GF_TTS_OUT=str(out_wav), GF_TTS_TEXT=str(txt))
    p = subprocess.run(["powershell", "-NoProfile", "-Command", _PS], capture_output=True, text=True,
                       timeout=timeout, env=env, stdin=subprocess.DEVNULL)
    txt.unlink(missing_ok=True)
    if p.returncode != 0 or not out_wav.exists() or out_wav.stat().st_size < 1000:
        raise TTSError(f"speech synthesis failed: {p.stderr.strip()[:300]}")
    return trim_silence(out_wav)
