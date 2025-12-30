import unittest

from plai.config import VideoSpec
from plai.io.normalization import RotationTransform


class RotationTransformTests(unittest.TestCase):
    def test_normalized_size_swaps_dimensions_for_right_angles(self) -> None:
        spec = VideoSpec(
            path="video.mp4",
            width=1920,
            height=1080,
            rotation=90,
            fps=30.0,
            duration=10.0,
        )
        transform = RotationTransform.from_video_spec(spec)
        self.assertEqual(transform.normalized_size, (1080, 1920))

    def test_point_roundtrip_for_90_degree_rotation(self) -> None:
        transform = RotationTransform(width=1920, height=1080, rotation=90)
        original = (100, 50)
        normalized = transform.to_normalized(original)
        restored = transform.to_original(normalized)
        self.assertEqual(restored, original)

    def test_point_roundtrip_for_270_degree_rotation(self) -> None:
        transform = RotationTransform(width=1080, height=1920, rotation=270)
        original = (20, 30)
        normalized = transform.to_normalized(original)
        restored = transform.to_original(normalized)
        self.assertEqual(restored, original)

    def test_invalid_rotation_raises(self) -> None:
        with self.assertRaises(ValueError):
            RotationTransform(width=100, height=200, rotation=45).to_normalized((0, 0))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
