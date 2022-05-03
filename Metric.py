"""Metric module"""

from datetime import datetime


class Metric:
    """
    Represents metric values.
    """

    def __init__(self,
                 plugin: str,
                 descriptor: str,
                 actual: float = None,
                 target: float = None,
                 text: str = None,
                 timestamp: datetime = None):
        self.plugin = self._sanitise_input(plugin)
        self.descriptor = self._sanitise_input(descriptor)
        self.actual = actual
        self.target = target
        self.text = text
        self.timestamp = timestamp

    @staticmethod
    def _sanitise_input(val: str):
        return val.replace(' ', '').lower()
