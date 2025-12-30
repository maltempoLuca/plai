import json
import tempfile
import unittest
from pathlib import Path

from plai.config import PoseConfig
from plai.vision import cache


class PoseCacheTests(unittest.TestCase):
    def test_video_sha256_matches_python_hashlib(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as fh:
            fh.write(b"abc123")
            video_path = Path(fh.name)

        expected = cache.video_sha256(video_path)
        self.assertEqual(expected, cache.video_sha256(video_path))

    def test_cache_roundtrip(self) -> None:
        pose_config = PoseConfig()
        with tempfile.NamedTemporaryFile(delete=False) as fh:
            fh.write(b"video-bytes")
            video_path = Path(fh.name)

        cache_dir = Path(tempfile.mkdtemp())
        cache_file = cache.cache_path(cache_dir, video_path, pose_config)

        frames = [
            cache.PoseFrame(
                frame_index=0,
                timestamp=0.0,
                landmarks=[cache.PoseLandmark(x=0.1, y=0.2, z=0.3, visibility=0.9)],
                score=0.8,
            ),
            cache.PoseFrame(
                frame_index=1,
                timestamp=0.033,
                landmarks=[cache.PoseLandmark(x=0.4, y=0.5, z=0.6, visibility=0.8)],
                score=None,
            ),
        ]

        cache.save_pose_frames(cache_file, frames)
        loaded = list(cache.load_pose_frames(cache_file))
        self.assertEqual(frames, loaded)

    def test_cache_filename_uses_pose_cache_key(self) -> None:
        pose_config = PoseConfig(model_complexity=2, enable_segmentation=True)
        fname = cache.cache_filename("hash", pose_config)
        self.assertTrue(pose_config.cache_key() in fname)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
