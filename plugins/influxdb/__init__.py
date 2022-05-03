"""
InfluxDB v1.x input plugin
"""

import urllib.parse

from influxdb import InfluxDBClient

from AppConfig import AppConfig
from plugins.PluginBase import OutputPluginBase


def _get_measurements(time, plugin, descriptor, actual, target, text, timestamp, logger):
    """
    Returns the actual, target, delta and text data points
    """

    record_actual = None
    record_target = None
    record_delta = None
    record_text = None

    def create_point(name: str, value: float):
        try:
            return {
                "measurement": name,
                "tags": {
                    "plugin": plugin,
                    "descriptor": descriptor
                },
                "time": time if timestamp is None else timestamp,
                "fields": {
                    "value": value
                }
            }
        except Exception as e:
            logger.exception(
                f'Error creating data point for {name}, plugin: {plugin}, descriptor: {descriptor}, value: {value}:\n{e}')
            return {}

    if actual is not None and actual != '':
        record_actual = create_point("actual", float(actual))

    if target is not None and target != '':
        record_target = create_point("target", float(target))

    if record_actual is not None and record_target is not None:
        record_delta = create_point("delta", float(actual) - float(target))

    if text is not None and text != '':
        record_text = create_point("text", str(text))

    return record_actual, record_target, record_delta, record_text


class Plugin(OutputPluginBase):
    """InfluxDB v1.x output Plugin immplementation"""

    def _read_configuration(self, config: AppConfig):
        section = config[self.plugin_name]
        self._hostname = section["hostname"]
        self._port = section["port"]
        self._database = section["database"]
        self._username = section["username"]
        self._password = section["password"]
        self._logger.debug(f'Influx Host: {self._hostname}:{self._port} Database: {self._database}')

    def __init__(self, config: AppConfig) -> None:
        super().__init__(config, 'InfluxDB', 'output')

    def _write_metrics(self, timestamp, metrics):
        """
        Writes the metrics to the database
        """

        influx_client = InfluxDBClient(self._hostname, self._port, self._username, self._password, self._database)

        data = []
        for metric in metrics:

            record_actual, record_target, record_delta, record_text = _get_measurements(timestamp,
                                                                                        metric.plugin,
                                                                                        metric.descriptor,
                                                                                        metric.actual,
                                                                                        metric.target,
                                                                                        metric.text,
                                                                                        metric.timestamp,
                                                                                        self._logger)

            if record_actual:
                data.append(record_actual)
            if record_target:
                data.append(record_target)
            if record_delta:
                data.append(record_delta)
            if record_text:
                data.append(record_text)

        try:
            if self._simulation is False:
                self._logger.debug('Writing all measurements to influx...')
                influx_client.write_points(data)
            else:
                self._logger.debug(f'Metrics to be written: {data}')
        except Exception as e:
            if hasattr(e, 'request'):
                self._logger.exception(
                    f'Error Writing to {self._database} at {self._hostname}:{self._port} - aborting write.\nRequest: {e.request.method} {urllib.parse.unquote(e.request.url)}\nBody: {e.request.body}.\nResponse: {e.response}\nError:{e}')
            else:
                self._logger.exception(
                    f'Error Writing to {self._database} at {self._hostname}:{self._port} - aborting write\nError:{e}')
