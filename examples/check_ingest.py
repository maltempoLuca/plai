"""Quick check for ingest helpers.

Generates a tiny 2-frame test clip with ffmpeg (red then green),
reads metadata, and iterates frames to print timestamps and pixel sums.
"""

from pathlib import Path

import numpy as np

from plai.io.ingest import iter_frames_with_timestamps, video_metadata


def main() -> None:
    clip = Path("examples/_tmp_ingest_test.mp4")
    # Generate a simple 2-frame 2x2 video: 1 red frame, 1 green frame.
    clip.parent.mkdir(parents=True, exist_ok=True)
    # fmt: off
    cmd = (
        "ffmpeg -y -hide_banner -loglevel error "
        "-f lavfi -i color=red:size=2x2:rate=1 -frames:v 1 "
        "-f lavfi -i color=green:size=2x2:rate=1 -frames:v 1 "
        "-filter_complex \"[0:v][1:v]concat=n=2:v=1:a=0\" "
        "-c:v libx264 -pix_fmt yuv420p "
        f"{clip}"
    )
    # fmt: on
    import subprocess

    subprocess.run(cmd, shell=True, check=True)

    meta = video_metadata(clip)
    print("metadata:", meta)

    frames = list(iter_frames_with_timestamps(clip, apply_rotation=True, max_frames=4))
    for ts, frame in frames:
        print(f"t={ts:.3f}s shape={frame.shape} sum={np.sum(frame)}")


if __name__ == "__main__":
    main()
