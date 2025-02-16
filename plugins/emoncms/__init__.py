"""
EMON CMS output plugin
"""

import time

import requests

from AppConfig import AppConfig
from plugins.PluginBase import OutputPluginBase


class Plugin(OutputPluginBase):
    """EMON CMS output Plugin immplementation"""

    def _read_configuration(self, config: AppConfig):
        api_key = config.get(self.plugin_name, "apiKey")
        node = config.get(self.plugin_name, "node")
        self._post_url = f'http://emoncms.org/input/post?apikey={api_key}&node={node}'

    def __init__(self, config: AppConfig) -> None:
        super().__init__(config, 'Emoncms', 'output')

    def _write_metrics(self, timestamp, metrics):
        """
        Writes the temperatures to emoncms.org
        """

        url = f'{self._post_url}&time={time.mktime(timestamp.timetuple())}&json={{'

        for metric in metrics:
            url = f'{url}{metric.descriptor} Actual: {str(metric.actual)},'
            if metric.target is not None:
                url += f'{metric.descriptor} Target: {str(metric.target)},'

        url += '}'
        url = url.replace(",}", "}")
        url = url.replace(" ", "")

        try:
            if self._simulation is False:
                self._logger.debug('URL: %s', url)
                with requests.get(url) as response:
                    self._logger.debug(
                        f'Emon API response from {url}: {response.status_code} {response.reason} {response.content}')  # pylint disable=W1201
                    response.raise_for_status()
        except requests.HTTPError as e:
            self._logger.exception(
                f'Emon API HTTPError from {url}: {response.status_code} {response.reason} - aborting write\nError: {e}')
        except Exception as e:
            self._logger.exception(f'Emon API error writing to {url} - aborting write\nError: {e}')
