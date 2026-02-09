#!/usr/bin/env python3
"""Generate Voicepeak audio files from a script.

Usage:
  python main.py <script_file> <output_dir>
"""
from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
import re

VOICEPEAK_EXE = r"C:\Program Files\VOICEPEAK\voicepeak"

SPEAKER_MAP = {
    "男性ナレーター": "Japanese Male 1",
    "男性登場人物": "Japanese Male 2",
    "女性登場人物": "Japanese Female 1",
}

NARRATOR_FLAG = "-n"
TEXT_FLAG = "-t"
OUTPUT_FLAG = "-o"
EMOTION_FLAG = "-"

LINE_PATTERN = re.compile(r"^\[(?P<person>[^/\]]+)\s*/\s*(?P<emotion>[^\]]+)\]\s*(?P<text>.+)$")


@dataclass(frozen=True)
class ScriptLine:
    speaker: str
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
        person = match.group("person").strip()
        emotion = match.group("emotion").strip()
        text = match.group("text").strip()
        if person not in SPEAKER_MAP:
            raise ValueError(f"Line {index} has an unknown person: {person}")
        lines.append(ScriptLine(speaker=SPEAKER_MAP[person], emotion=emotion, text=text))
    return lines


def build_command(script_line: ScriptLine, output_path: Path, text_path: Path) -> list[str]:
    command = [
        VOICEPEAK_EXE,
        NARRATOR_FLAG,
        script_line.speaker,
        OUTPUT_FLAG,
        str(output_path),
        TEXT_FLAG,
        str(text_path),
    ]
    if script_line.emotion.lower() != "none":
        command.extend([EMOTION_FLAG, script_line.emotion])
    return command


def run(script_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    script_lines = parse_script(script_path)
    for index, script_line in enumerate(script_lines, start=0):
        output_path = output_dir / f"{index:03}.wav"
        text_path = output_dir / f"{index:03}.txt"
        text_path.write_text(sanitize_text(script_line.text), encoding="utf-8")
        command = build_command(script_line, output_path, text_path)
        subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Voicepeak audio files from a script file.")
    parser.add_argument("script_file", type=Path, help="Path to the script file.")
    parser.add_argument("output_dir", type=Path, help="Directory to write wav files.")
    args = parser.parse_args()
    run(args.script_file, args.output_dir)


if __name__ == "__main__":
    main()
