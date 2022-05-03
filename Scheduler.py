"""
Helpers for scheduling tasks.
"""

import logging
from datetime import datetime

from croniter import croniter


class Scheduler:

    def __init__(self, plugin_name: str, polling_interval: str) -> None:
        self.__logger = logging.getLogger('scheduler')
        self.plugin_name = plugin_name
        self.polling_interval = self._validate_interval(polling_interval)

    def _validate_interval(self, interval: str) -> str:
        """
        This function ensures the minimum duration allowed to be specified is 60s, regardless of whether a
        cron-style interval or integer is specified.
        """

        if croniter.is_valid(interval):
            base_date = datetime.utcnow().replace(second=0, microsecond=0, minute=0)
            cron = croniter(interval, base_date)
            next_run = (cron.get_next(datetime) - base_date).total_seconds()
            if next_run < 60:
                self.__logger.warning(
                    f'[{self.plugin_name}-plugin] Supplied cron-style interval \'{interval}\' has a frequency of less than 60s.  Defaulting to \'* * * * *\'.'
                )
                ret_val = '* * * * *'
            else:
                self.__logger.debug(
                    f'[{self.plugin_name}-plugin] User Specified Cron of \'{interval}\' is valid, and equates to an interval of {next_run} Seconds.')
                ret_val = interval
        else:
            self.__logger.error(
                f'[{self.plugin_name}-plugin] Value provided to Scheduler is not a valid Cron String: \'{interval}\'.  Defaulting to \'* * * * *\'.')
            ret_val = '* * * * *'

        return ret_val

    def can_run_now(self) -> bool:
        return croniter.match(self.polling_interval, datetime.utcnow())

    def time_until_next_run(self) -> float:
        cur_run_time = datetime.utcnow()
        cron = croniter(self.polling_interval, cur_run_time)
        next_run = cron.get_next(datetime)
        return float((next_run - cur_run_time).total_seconds())
