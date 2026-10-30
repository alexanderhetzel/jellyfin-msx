"""Generate a small synthetic Direct Play fixture locally, never on Ultra.cc."""

import argparse
import shutil
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / ".lab/media/MSX Playback Test (2026).mp4",
    )
    args = parser.parse_args()
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        parser.error("Install FFmpeg locally to create this fixture. Do not encode on Ultra.cc.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-n",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=1280x720:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000",
            "-t",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-profile:v",
            "main",
            "-level:v",
            "3.1",
            "-pix_fmt",
            "yuv420p",
            "-b:v",
            "1000k",
            "-maxrate",
            "1500k",
            "-bufsize",
            "3000k",
            "-colorspace",
            "bt709",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-color_range",
            "tv",
            "-g",
            "48",
            "-c:a",
            "aac",
            "-ac",
            "2",
            "-b:a",
            "128k",
            "-af",
            "volume=0.1",
            "-movflags",
            "+faststart",
            "-metadata",
            "title=MSX Playback Test",
            str(args.output),
        ],
        check=True,
    )
    print(args.output)


if __name__ == "__main__":
    main()
