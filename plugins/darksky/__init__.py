"""
DarkSky input plugin - for getting the outside temperature
"""

import urllib.parse
from datetime import timedelta
from time import mktime

import forecastio
import pytz

from AppConfig import AppConfig
from Metric import *
from Scheduler import Scheduler
from plugins.PluginBase import InputPluginBase


class Plugin(InputPluginBase):
    """DarkSky input Plugin immplementation"""

    def _read_configuration(self, config: AppConfig):
        section = config[self.plugin_name]
        self._api_key = section['apiKey']
        self._latitude = section['latitude']
        self._longitude = section['longitude']
        self._zone = config.get_string_or_default(self.plugin_name, 'Outside', 'Outside')
        self._logger.debug("Outside Zone: %s", self._zone)
        self._plugin_name_override = 'weather'

        self.scheduler = Scheduler(plugin_name=self.plugin_name,
                                   polling_interval=config.get_string_or_default(self.plugin_name,
                                                                                 'pollingInterval',
                                                                                 '* * * * *')
                                   )

    def __init__(self, config: AppConfig) -> None:
        super().__init__(config, 'DarkSky', 'input')

    @staticmethod
    def _dt(u: int):
        return datetime.fromtimestamp(u)

    @staticmethod
    def _ut(d):
        return mktime(d.timetuple())

    @staticmethod
    def _round_time(dt=None, round_to=60):
        """Round a datetime object to any time laps in seconds
       dt : datetime.datetime object, default now.
       roundTo : Closest number of seconds to round to, default 1 minute.
       Author: Thierry Husson 2012 - Use it as you want but don't blame me.
       """
        if dt is None:
            dt = datetime.utcnow()
        seconds = (dt - dt.min).seconds
        # // is a floor division, not a comment on following line:
        rounding = (seconds + round_to / 2) // round_to * round_to
        return dt + timedelta(0, rounding - seconds, -dt.microsecond)

    @staticmethod
    def _is_number(s):
        try:
            n = str(float(s))
            if n == "nan" or n == "inf" or n == "-inf": return False
        except ValueError:
            try:
                complex(s)  # for complex
            except ValueError:
                return False
        except:
            return False
        return True

    # pylint disable=E1101
    def _read_metrics(self):
        """
        Reads the outside temperature from DarkSky
        """

        if not self.scheduler.can_run_now():
            self._logger.debug("Not running as not within Cron window!")
            return [], ''

        weather_data = []
        text_weather = ''

        if self._simulation:
            weather_metric = [
                Metric(plugin=self._plugin_name_override,
                       descriptor='OutsideTemp',
                       actual=1.0,
                       timestamp=datetime.utcnow().replace(second=0, microsecond=0)
                       ),
                Metric(plugin=self._plugin_name_override,
                       descriptor='WeatherIcon',
                       text="cloudy",
                       timestamp=datetime.utcnow().replace(second=0, microsecond=0)
                       )
            ]
            text_weather += f'{weather_metric[0].descriptor} ({weather_metric[0].actual} A, {weather_metric[0].timestamp} TS), {weather_metric[1].descriptor} ({weather_metric[1].text} S, {weather_metric[1].timestamp} TS), '
            return weather_metric, text_weather
        else:
            try:
                forecast = forecastio.load_forecast(self._api_key, self._latitude, self._longitude)
            except Exception as e:
                if hasattr(e, 'request'):
                    self._logger.exception(
                        f'DarkSky API Error reading from {e.request.method} {urllib.parse.unquote(e.request.url)}\nResponse: {e.response.json()}\nError:{e}')
                else:
                    self._logger.exception(f'DarkSky API error - aborting read:\n{e}')
                return []

            # Loop through forecastio.json, we want all the metrics.
            if 'time' in forecast.json['currently']:
                dt_stamp = self._dt(int(forecast.json['currently']['time']))
            else:
                return [], ''

            for tdata in forecast.json['currently']:
                if "time" not in tdata:
                    ts = str(forecast.json['currently'][tdata])
                    if ts.endswith("%"):
                        ts = ts[:-1]
                    if self._is_number(ts):
                        weather_metric = Metric(plugin=self._plugin_name_override,
                                                descriptor=tdata,
                                                actual=float(ts),
                                                timestamp=self._dt(int(round(
                                                    self._ut(self._round_time(dt=dt_stamp, round_to=60))))).astimezone(
                                                    pytz.utc).replace(tzinfo=None))
                        text_weather += f'{weather_metric.descriptor} ({weather_metric.actual} A, {weather_metric.timestamp} TS)'
                        weather_data.append(weather_metric)
                    else:
                        if not ts == "NA":
                            weather_metric = Metric(plugin=self._plugin_name_override,
                                                    descriptor=tdata,
                                                    text=ts,
                                                    timestamp=self._dt(int(round(self._ut(
                                                        self._round_time(dt=dt_stamp, round_to=60))))).astimezone(
                                                        pytz.utc).replace(tzinfo=None))

                            text_weather += f'{weather_metric.descriptor} ("{weather_metric.text}" S) ({weather_metric.timestamp} TS)'
                            weather_data.append(weather_metric)

        return weather_data, text_weather
