"""
DCC Polling via n3rgy consumer-facing API
"""

import json
import random
from datetime import timedelta

import requests

from AppConfig import AppConfig
from Metric import *
from Scheduler import Scheduler
from plugins.PluginBase import InputPluginBase


class Plugin(InputPluginBase):
    """DCC Api Ingestion"""

    def _read_configuration(self, config: AppConfig):
        self._config = config
        section = config[self.plugin_name]
        self._mprn = section['mprn']
        self._apikey = section['apikey']
        self._gas_calorific = float(section['gas_calorific_value'])
        self._backfill_period = int(section['backfill_period'])
        self.scheduler = Scheduler(plugin_name=self.plugin_name,
                                   polling_interval=config.get_string_or_default(self.plugin_name,
                                                                                 'pollingInterval',
                                                                                 '* * * * *')
                                   )

    def __init__(self, config: AppConfig) -> None:
        super().__init__(config, 'DCCApi', 'input')

    @staticmethod
    def _adjust_dt(dt: str, period: int) -> str:
        rdt = datetime.strptime(dt, '%Y%m%d%H%M') - timedelta(hours=period)
        return rdt.strftime('%Y%m%d%H%M')

    def _m3_to_kwh(self, unit: float) -> float:
        return round((unit * self._gas_calorific * 1.02264 / 3.6), 3) if unit < 100 else 0

    def _get_dcc_data(self, api_endpoint: str = "", start_range: int = 0, end_range: int = 0) -> json:
        base_url = f'https://consumer-api.data.n3rgy.com/{api_endpoint}'
        headers = {'Authorization': self._apikey}

        if start_range != 0 and end_range != 0:
            base_url = f'{base_url}?start={start_range}&end={end_range}'

        rdata = json.loads(requests.get(url=base_url, headers=headers).content)

        if 'Message' in rdata:
            self._logger.error(rdata['Message'])
            return None

        return rdata

    def _get_consumption_data(self, fuel: str, period: int) -> json:
        recent_consumption = self._get_dcc_data(api_endpoint=f'{fuel}/consumption/1')

        if 'availableCacheRange' not in recent_consumption:
            self._logger.debug(f'No consumption data available for {fuel}')
            return None

        end_range = recent_consumption['availableCacheRange']['end']
        start_range = self._adjust_dt(dt=end_range, period=period)

        latest_consumption = \
            self._get_dcc_data(api_endpoint=f"{fuel}/consumption/1?start={start_range}&end={end_range}")[
                'values']

        return latest_consumption

    def _process_dcc_data(self):
        energy_data = []
        text_data = ''

        if self._simulation:
            # Return some random consumption data if simulating a read
            energy_data = [
                Metric(
                    plugin=self.plugin_name,
                    descriptor='gas',
                    actual=round(random.uniform(0.0, 7.0), 2),
                    timestamp=datetime.utcnow().replace(second=0, microsecond=0)),
                Metric(
                    plugin=self.plugin_name,
                    descriptor='electricity',
                    actual=round(random.uniform(0.0, 7.0), 2),
                    timestamp=datetime.utcnow().replace(second=0, microsecond=0)
                )
            ]
            text_data = f'{energy_data[0].descriptor} ({energy_data[0].actual} A, {energy_data[0].timestamp} TS) {energy_data[1].descriptor} ({energy_data[1].actual} A, {energy_data[1].timestamp} TS)'

            return energy_data, text_data

        #tdata = self._get_dcc_data()

        #if 'entries' not in tdata:
        #    self._logger.error('Unable to get a list of Fuel types.')
        #    return None

        #for key in tdata['entries']:
        for key in ['gas', 'electricity']:
            t_fuel_data = self._get_consumption_data(fuel=key, period=self._backfill_period)

            for consumption in t_fuel_data:
                consumption_kwh = self._m3_to_kwh(consumption['value']) if key == "gas" else consumption['value']
                energy_data.append(Metric(plugin=self.plugin_name,
                                          descriptor=key,
                                          actual=consumption_kwh,
                                          timestamp=datetime.strptime(f"{consumption['timestamp']}:00",
                                                                      '%Y-%m-%d %H:%M:%S')))

                text_data += f"{key} ({consumption_kwh} A, {consumption['timestamp']}:00 TS)"

        return energy_data, text_data

    def _read_metrics(self):
        """
        Reads all consumption metrics.
        """

        if not self.scheduler.can_run_now():
            self._logger.info('Not running as not within Cron window!')
            return [], ''

        dcc_data, dcc_text = self._process_dcc_data()

        if dcc_data is None:
            self._logger.error('No data was retrieved.')
            return [], ''

        self._logger.debug(dcc_text)

        return dcc_data, dcc_text
