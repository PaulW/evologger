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

        def _add_seperator(text: str, newval: str):
            if text != '':
                return f', {newval}'
            else:
                return newval

        text_metrics = ''
        for metric in metrics:
            text_metrics_tmp = ''
            text_metrics_tmp += f'{metric.actual} A' if metric.actual else ''
            text_metrics_tmp += f'{_add_seperator(text_metrics_tmp, metric.target)} T' if metric.target else ''
            text_metrics_tmp += f'{_add_seperator(text_metrics_tmp, metric.text)} S' if metric.text else ''
            text_metrics_tmp += f'{_add_seperator(text_metrics_tmp, metric.timestamp)} TS' if metric.timestamp else ''

            text_metrics += f'{_add_seperator(text_metrics, f"{metric.plugin}.{metric.descriptor} ({text_metrics_tmp})")}'

        if self._simulation is False:
            self._logger.info(text_metrics)
