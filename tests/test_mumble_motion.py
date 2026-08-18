from __future__ import annotations

from types import SimpleNamespace
import unittest

from gw2helper.services.mumble import MumbleLinkMotionTracker


class _Clock:
    def __init__(self, value: float) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


class _Link:
    def __init__(self, positions: list[tuple[float, float, float]]) -> None:
        self._positions = iter(positions)
        self.closed = False

    def read(self):
        return SimpleNamespace(fAvatarPosition=next(self._positions)), None

    def close(self) -> None:
        self.closed = True


class MumbleLinkMotionTrackerTests(unittest.TestCase):
    def test_reports_movement_until_avatar_position_stabilizes(self) -> None:
        clock = _Clock(100.0)
        link = _Link(((0.0, 0.0, 0.0), (0.4, 0.0, 0.0), (0.4, 0.0, 0.0)))
        tracker = MumbleLinkMotionTracker(link_factory=lambda: link, clock=clock)

        self.assertFalse(tracker.is_moving())
        clock.value = 100.1
        self.assertTrue(tracker.is_moving())
        clock.value = 100.5
        self.assertFalse(tracker.is_moving())

        tracker.close()
        self.assertTrue(link.closed)