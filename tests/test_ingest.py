import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from plai.config import VideoSpec
from plai.io import ingest


class IngestTests(unittest.TestCase):
    def test_parse_rational_handles_fraction_and_zero(self) -> None:
        self.assertAlmostEqual(ingest._parse_rational("30000/1001"), 29.97002997)
        self.assertEqual(ingest._parse_rational("0/0"), 0.0)
        self.assertEqual(ingest._parse_rational("24"), 24.0)

    def test_rotation_prefers_tags_and_normalizes(self) -> None:
        stream = {"tags": {"rotate": "450"}}
        self.assertEqual(ingest._rotation_from_stream(stream), 90)

        stream = {"side_data_list": [{"rotation": -90}]}
        self.assertEqual(ingest._rotation_from_stream(stream), 270)

    def test_iter_expected_timestamps_uses_frame_count_if_available(self) -> None:
        spec = VideoSpec(
            path=Path("dummy.mp4"),
            width=1920,
            height=1080,
            rotation=0,
            fps=30.0,
            duration=10.0,
            frame_count=3,
        )
        timestamps = list(ingest.iter_expected_timestamps(spec))
        self.assertEqual(
            timestamps,
            [
                (0, 0.0),
                (1, 1 / 30),
                (2, 2 / 30),
            ],
        )

    def test_probe_video_parses_ffprobe_output(self) -> None:
        sample_probe = {
            "streams": [
                {
                    "codec_type": "video",
                    "width": 1280,
                    "height": 720,
                    "avg_frame_rate": "24000/1001",
                    "tags": {"rotate": "90"},
                    "nb_frames": "240",
                }
            ],
            "format": {"duration": "10.0"},
        }

        with tempfile.NamedTemporaryFile(suffix=".mp4") as fh:
            video_path = Path(fh.name)
            with mock.patch.object(
                ingest.subprocess, "check_output", autospec=True
            ) as mock_ffprobe:
                mock_ffprobe.return_value = json.dumps(sample_probe)
                spec = ingest.probe_video(video_path)

        self.assertEqual(spec.width, 1280)
        self.assertEqual(spec.height, 720)
        self.assertEqual(spec.rotation, 90)
        self.assertAlmostEqual(spec.fps, 23.9760239, places=5)
        self.assertEqual(spec.frame_count, 240)
        self.assertAlmostEqual(spec.duration, 10.0)


if __name__ == "__main__":  # pragma: no cover - manual invocation helper
    unittest.main()
