"""
CSV file output plugin
"""

import csv
import os.path

from AppConfig import AppConfig
from plugins.PluginBase import OutputPluginBase


class Plugin(OutputPluginBase):
    """CSV output Plugin immplementation"""

    def _read_configuration(self, config: AppConfig):
        self._filename = config.get(self.plugin_name, "filename")

    def __init__(self, config: AppConfig) -> None:
        super().__init__(config, 'Csv', 'output')

    def _write_metrics(self, timestamp, metrics):
        """
        Writes the temperatures to the configured file
        """

        csv_file = None
        writer = None

        try:
            csv_write_headers = not self._simulation and not os.path.isfile(self._filename)

            if not self._simulation:
                try:
                    csv_file = open(self._filename, 'a', encoding='UTF-8')
                except Exception as e:
                    self._logger.exception(f'Error opening {self._filename} for writing - aborting write\n{e}')

                writer = csv.writer(csv_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)

            if not self._simulation and csv_write_headers:

                self._logger.debug(f'Creating {self._filename}')

                fieldnames = ['Time']
                for metric in metrics:
                    if metric.actual is not None:
                        fieldnames.append(metric.descriptor + ' [A]')
                    if metric.target is not None:
                        fieldnames.append(metric.descriptor + ' [T]')
                    if metric.text is not None:
                        fieldnames.append(metric.descriptor + ' [S]')

                writer.writerow(fieldnames)

            row = [timestamp]
            for metric in metrics:
                if metric.actual is not None:
                    row.append(metric.actual)

                if metric.target is not None:
                    row.append(metric.target)

                if metric.text is not None:
                    row.append(metric.text)

        finally:
            if self._simulation is False and writer is not None:
                writer.writerow(row)
                csv_file.close()
