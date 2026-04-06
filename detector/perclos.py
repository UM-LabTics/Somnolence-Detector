import time
from collections import deque


class PerclosTracker:
    """Tracks PERCLOS (PERcentage of eye CLOSure) over a time window.

    PERCLOS = fraction of time eyes are closed within the window.
    Standard drowsiness indicator from FHWA/NHTSA research.
    P80 criterion: PERCLOS > 80% indicates severe drowsiness.
    """

    def __init__(self, window_seconds=60.0, ear_threshold=0.21):
        """
        Args:
            window_seconds: Time window for PERCLOS calculation (default 60s).
            ear_threshold: EAR below which eyes are considered closed.
        """
        self._window = window_seconds
        self._ear_threshold = ear_threshold
        self._history = deque()  # deque of (timestamp, is_closed)

    def update(self, ear_value, timestamp=None):
        """Record a new EAR sample.

        Args:
            ear_value: Current average EAR value.
            timestamp: Time of sample (default: time.monotonic()).
        """
        if timestamp is None:
            timestamp = time.monotonic()

        is_closed = ear_value < self._ear_threshold
        self._history.append((timestamp, is_closed))

        # Purge entries older than window
        cutoff = timestamp - self._window
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

    def get_perclos(self):
        """Calculate current PERCLOS value.

        Returns:
            Float between 0.0 and 1.0. Returns 0.0 if no samples.
        """
        if not self._history:
            return 0.0

        closed_count = sum(1 for _, closed in self._history if closed)
        return closed_count / len(self._history)

    def reset(self):
        """Clear all history."""
        self._history.clear()
