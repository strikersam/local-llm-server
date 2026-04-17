import time
from typing import Dict


class NavigationMetrics:
    def __init__(self):
        self.metrics = {}

    def record_measure(self, name: str, data: Dict):
        self.metrics[name] = data

    def get_metrics(self):
        return self.metrics


navigation_metrics = NavigationMetrics()


def record_content_visible():
    navigation_metrics.record_measure("content_visible", {
        "timestamp": time.time(),
        "data": "TemplateDetailsPage"
    })


def get_navigation_metrics():
    return navigation_metrics.get_metrics()
