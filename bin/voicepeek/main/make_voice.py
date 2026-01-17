#!/usr/bin/env python3
"""Generate Voicepeak audio files from a script.

Usage:
  python make_voice.py <script_file> <output_dir> [merged_output]
"""
from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
import re
import tempfile
import wave

FIXED_SPEAKER = "Japanese Female 1"
DEFAULT_VOICEPEAK_EXE = r"C:\Program Files\VOICEPEAK\voicepeak.exe"

NARRATOR_FLAG = "-n"
TEXT_FLAG = "-t"
OUTPUT_FLAG = "-o"
EMOTION_FLAG = "-"

LINE_PATTERN = re.compile(r"^\[(?P<emotion>[^\]]+)\]\s*(?P<text>.+)$")


@dataclass(frozen=True)
class ScriptLine:
    emotion: str
    text: str


def sanitize_text(text: str) -> str:
    text = text.replace("\\n", " ")
    text = text.replace("\r", " ").replace("\n", " ")
    return re.sub(r" {2,}", " ", text).strip()


def parse_script(script_path: Path) -> list[ScriptLine]:
    lines: list[ScriptLine] = []
    for index, raw_line in enumerate(script_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        match = LINE_PATTERN.match(stripped)
        if not match:
            raise ValueError(f"Line {index} is not in the expected format: {raw_line}")
        emotion = match.group("emotion").strip()
        text = match.group("text").strip()
        lines.append(ScriptLine(emotion=emotion, text=text))
    return lines


def build_command(script_line: ScriptLine, output_path: Path, text_path: Path, voicepeak_exe: str) -> list[str]:
    command = [
        voicepeak_exe,
        NARRATOR_FLAG,
        FIXED_SPEAKER,
        OUTPUT_FLAG,
        str(output_path),
        TEXT_FLAG,
        str(text_path),
    ]
    if script_line.emotion.lower() != "none":
        command.extend([EMOTION_FLAG, script_line.emotion])
    return command


def _sample_format_for_width(sampwidth: int) -> str:
    formats = {1: "u8", 2: "s16", 3: "s24", 4: "s32"}
    if sampwidth not in formats:
        raise ValueError(f"Unsupported sample width: {sampwidth} bytes")
    return formats[sampwidth]


def _convert_wav_to_match(
    wav_path: Path,
    target_params: wave._wave_params,
    temp_dir: Path,
) -> Path:
    target_channels = target_params.nchannels
    target_width = target_params.sampwidth
    target_rate = target_params.framerate
    sample_fmt = _sample_format_for_width(target_width)
    output_path = temp_dir / f"{wav_path.stem}_converted.wav"
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(wav_path),
        "-ac",
        str(target_channels),
        "-ar",
        str(target_rate),
        "-sample_fmt",
        sample_fmt,
        str(output_path),
    ]
    example = (
        f"ffmpeg -y -i {wav_path} -ac {target_channels} -ar {target_rate} "
        f"-sample_fmt {sample_fmt} {output_path}"
    )
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "ffmpeg was not found while attempting to convert wav files.\n"
            f"Command: {' '.join(command)}\n"
            f"Example: {example}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        error_message = exc.stderr.strip() or exc.stdout.strip()
        raise RuntimeError(
            "Failed to convert wav file with ffmpeg.\n"
            f"Command: {' '.join(command)}\n"
            f"Example: {example}\n"
            f"Error output:\n{error_message}"
        ) from exc
    return output_path


def concat_wav_files(wav_paths: list[Path], merged_output: Path) -> None:
    if not wav_paths:
        raise ValueError("No wav files were generated to concatenate.")
    with wave.open(str(wav_paths[0]), "rb") as first_wav:
        params = first_wav.getparams()
    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        prepared_paths: list[Path] = [wav_paths[0]]
        for wav_path in wav_paths[1:]:
            with wave.open(str(wav_path), "rb") as wav_file:
                if wav_file.getparams()[:4] == params[:4]:
                    prepared_paths.append(wav_path)
                    continue
            prepared_paths.append(_convert_wav_to_match(wav_path, params, temp_dir))
        frames: list[bytes] = []
        for wav_path in prepared_paths:
            with wave.open(str(wav_path), "rb") as wav_file:
                frames.append(wav_file.readframes(wav_file.getnframes()))
    merged_output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(merged_output), "wb") as output_wav:
        output_wav.setparams(params)
        for frame in frames:
            output_wav.writeframes(frame)


def run(script_path: Path, output_dir: Path, voicepeak_exe: str, merged_output: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    script_lines = parse_script(script_path)
    for index, script_line in enumerate(script_lines, start=1):
        output_path = output_dir / f"{index:03}.wav"
        text_path = output_dir / f"{index:03}.txt"
        text_path.write_text(sanitize_text(script_line.text), encoding="utf-8")
        command = build_command(script_line, output_path, text_path, voicepeak_exe)
        subprocess.run(command, check=True)
    wav_paths = sorted(output_dir.glob("*.wav"), key=lambda path: path.name)
    if merged_output.resolve() in {path.resolve() for path in wav_paths}:
        wav_paths = [path for path in wav_paths if path.resolve() != merged_output.resolve()]
    concat_wav_files(wav_paths, merged_output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Voicepeak audio files from a script file.")
    parser.add_argument("script_file", type=Path, help="Path to the script file.")
    parser.add_argument("output_dir", type=Path, help="Directory to write wav files.")
    parser.add_argument(
        "merged_output",
        nargs="?",
        type=Path,
        help="Output path for the merged wav file (defaults to <output_dir>/merged.wav).",
    )
    args = parser.parse_args()
    merged_output = args.merged_output or (args.output_dir / "merged.wav")
    run(args.script_file, args.output_dir, DEFAULT_VOICEPEAK_EXE, merged_output)


if __name__ == "__main__":
    main()
