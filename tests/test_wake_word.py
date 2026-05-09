import unittest

from engine.wake_word import WakeWordSmoother, recommend_threshold


class WakeWordTests(unittest.TestCase):
    def test_smoother_requires_multiple_hits(self):
        smoother = WakeWordSmoother(("jarvis",), window_size=4, required_hits=2, threshold=0.35)

        trigger, scores = smoother.update({"jarvis": 0.4})
        self.assertIsNone(trigger)
        self.assertGreaterEqual(scores["jarvis"], 0.35)

        trigger, scores = smoother.update({"jarvis": 0.5})
        self.assertEqual(trigger, "jarvis")
        self.assertGreaterEqual(scores["jarvis"], 0.35)

    def test_recommended_threshold_handles_noise(self):
        self.assertEqual(recommend_threshold(2000, 0.35), 0.5)
        self.assertEqual(recommend_threshold(100, 0.45), 0.35)
        self.assertEqual(recommend_threshold(400, 0.35), 0.35)


if __name__ == "__main__":
    unittest.main()
