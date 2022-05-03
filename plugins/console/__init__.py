"""
Console output plugin
"""

from AppConfig import AppConfig
from plugins.PluginBase import OutputPluginBase


class Plugin(OutputPluginBase):
    """Console output Plugin immplementation"""

    def _read_configuration(self, config: AppConfig):
        self._hot_water = config.get_string_or_default('DEFAULT', 'HotWater', None)

    def __init__(self, config: AppConfig) -> None:
        super().__init__(config, 'Console', 'output')

    def _write_metrics(self, timestamp, metrics):
        """
        Writes the temperatures to the console
        """

        text_metrics = ''
        for metric in metrics:
            text_metrics += f'{metric.plugin}.{metric.descriptor} ('

            if metric.actual is not None:
                text_metrics += f'{metric.actual} A'

            if metric.target is not None:
                text_metrics += f', {metric.target} T'

            if metric.text is not None:
                text_metrics += f', {metric.text} S'

            text_metrics += ') '

        if self._simulation is False:
            self._logger.info(text_metrics)
