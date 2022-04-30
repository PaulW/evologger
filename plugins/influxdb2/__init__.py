"""
InfluxDB v2.x input plugin
"""

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from AppConfig import AppConfig
from plugins.PluginBase import OutputPluginBase


def _get_measurements(time, plugin, descriptor, actual, target, text, logger):
    """
    Returns the actual, target, delta and text data points
    """

    record_actual = None
    record_target = None
    record_delta = None
    record_text = None

    def create_point(name: str, value: float):
        try:
            return Point(name).time(time).tag("descriptor", descriptor).field("value", value)
        except Exception as e:
            logger.exception(
                f'Error creating data point for {name}, plugin: {plugin}, descriptor: {descriptor}, value: {value}:\n{e}')
            return Point(name)

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
    """InfluxDB v2.x output Plugin immplementation"""

    def _read_configuration(self, config: AppConfig):
        section = config[self.plugin_name]
        self._hostname = section["hostname"]
        self._port = section["port"]
        self._org = section["org"]
        self._bucket = section["bucket"]
        self._apikey = section["apikey"]
        self._logger.debug(f'Influx Host: {self._hostname}:{self._port} Org: {self._org}, Bucket:{self._bucket}')

    def __init__(self, config: AppConfig) -> None:
        super().__init__(config, 'InfluxDB2', 'output')

    def _write_metrics(self, timestamp, metrics):
        """
        Writes the metrics to the org bucket
        """

        influx_client = InfluxDBClient(url=f'{self._hostname}:{self._port}', token=self._apikey, org=self._org)
        write_api = influx_client.write_api(write_options=SYNCHRONOUS)

        data = []
        for metric in metrics:

            record_actual, record_target, record_delta, record_text = _get_measurements(timestamp, metric.plugin,
                                                                                        metric.descriptor,
                                                                                        metric.actual, metric.target,
                                                                                        metric.text,
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
                write_api.write(bucket=self._bucket, record=data)
        except Exception as e:
            if hasattr(e, 'response'):
                if e.response.status == 401:
                    self._logger.exception(
                        f'Insufficient write permissions to Bucket: "{self._bucket}" - aborting write\nError:{e}')
                else:
                    self._logger.exception(
                        f'Error Writing to {self._bucket} at {self._hostname}:{self._port} - aborting write.\nResponse: {e.body.json()}\nError:{e}')
            else:
                self._logger.exception(
                    f'Error Writing to {self._bucket} at {self._hostname}:{self._port} - aborting write\nError:{e}')
