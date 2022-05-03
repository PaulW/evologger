"""
Helpers for scheduling tasks.
"""

import logging
from datetime import datetime

from croniter import croniter


class Scheduler:

    def __init__(self, polling_interval: str) -> None:
        self.__logger = logging.getLogger('scheduler')
        self.polling_interval = polling_interval

    def _is_cron(self) -> bool:
        return croniter.is_valid(self.polling_interval)

    def can_run_now(self):
        return True

    def time_until_next_run(self) -> float:
        ret_val = 60
        if self._is_cron():
            cur_run_time = datetime.utcnow()
            cron = croniter(self.polling_interval, cur_run_time)
            next_run = cron.get_next(datetime)
            ret_val = (next_run - cur_run_time).total_seconds()
        else:
            if self.polling_interval.isdigit():
                ret_val = float(self.polling_interval)
                if ret_val < 60:
                    self.__logger.warning(
                        f'Manually specified Intervals of less than 60 seconds is not allowed!  Defaulting to 60s.')
                    ret_val = 60
            else:
                self.__logger.error(
                    f'Value provided to Scheduler is neither an Number or valid Cron String: \'{self.polling_interval}\'.  Defaulting to 60s.')
        return ret_val
