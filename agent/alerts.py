import logging

logger = logging.getLogger(__name__)


class AlertChecker:
    def __init__(self, threshold: int = 20):
        self.threshold = threshold

    def should_alert(self, previous_score: int, new_score: int) -> bool:
        drop = previous_score - new_score
        return drop >= self.threshold
