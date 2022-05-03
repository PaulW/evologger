#!/usr/bin/env python3

"""
EvoHome loging application
Reads temperatures from configured input plugins and writes them to configured output plugins
"""
# pylint: disable=global-statement

import getopt
import http
import logging.config
import signal
import sys
import time
from datetime import datetime

import structlog

from AppConfig import AppConfig
from Scheduler import Scheduler
from pluginloader import PluginLoader

logger = None
plugins = None
logging.raiseExceptions = True
continue_polling = True
config = AppConfig('config.ini')


def handle_signal(sig, _):
    """
    SIGTERM/SIGINT signal handler to flag the application to stop.
    """

    signal_name = signal.Signals(sig).name
    msg = f'Signal {signal_name} received, terminating the application.'
    if logger is not None:
        logger.info(msg)
    else:
        print(msg)
    global continue_polling
    continue_polling = False

    raise SystemExit(msg)


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


def configure_logging(log_level):
    """
    Configures logging using structlog
    """
    timestamper = structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S")
    pre_chain = [
        # Add the log level and a timestamp to the event_dict if the log entry
        # is not from structlog.
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        # Add extra attributes of LogRecord objects to the event dictionary
        # so that values passed in the extra parameter of log methods pass
        # through to log output.
        structlog.stdlib.ExtraAdder(),
        timestamper,
    ]
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "plain": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.dev.ConsoleRenderer(colors=False),
                ],
                "foreign_pre_chain": pre_chain,
            },
            "colored": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.dev.ConsoleRenderer(colors=True),
                ],
                "foreign_pre_chain": pre_chain,
            },
        },
        "handlers": {
            "default": {
                "level": logging.getLevelName(log_level),
                "class": "logging.StreamHandler",
                "formatter": "colored",
            },
            "file": {
                "level": logging.getLevelName(logging.DEBUG),
                "class": "logging.handlers.WatchedFileHandler",
                "filename": "evologger.log",
                "formatter": "plain",
            },
        },
        "loggers": {
            "": {
                "handlers": ["default", "file"],
                "level": "DEBUG",
                "propagate": True,
            },
        }
    })

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    global logger
    logger = structlog.get_logger('evohome-logger')

    if config.get_boolean_or_default('DEFAULT', 'httpDebug', False) is True:
        http_logger = structlog.get_logger('http-logger')

        def print_http_debug_to_log(*args):
            http_logger.debug(" ".join(args))

        http.client.HTTPConnection.debuglevel = 5
        http.client.print = print_http_debug_to_log


def read_metrics():
    """
    Reads the metrics from the input plugins
    """
    metrics = []
    for i in plugins.inputs:
        plugin = plugins.load(i)
        if plugin is None:
            logger.error("plugin is none!: %s", i)
        else:
            try:
                temps = plugin.read()
                if not temps:
                    continue

            except Exception as e:
                logger.exception("Error reading temps from %s: %s", plugin.plugin_name, str(e))
                return []

            for t in temps:
                metrics.append(t)

    # Sort by zone name, with hot water on the end and finally 'Outside'
    metrics = sorted(metrics,
                     key=lambda t: (t.plugin, t.descriptor))
    return metrics


def publish_metrics(metrics):
    """
    Publishes the metrics to the output plugins
    """

    if metrics:
        timestamp = datetime.utcnow()
        timestamp = timestamp.replace(microsecond=0)

        text_metrics = f'{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}: '

        for metric in metrics:
            text_metrics += f'{metric.plugin}.{metric.descriptor} ('

            if metric.actual is not None:
                text_metrics += f' {metric.actual} A'

            if metric.target is not None:
                text_metrics += f' {metric.target} T'

            if metric.text is not None:
                text_metrics += f' {metric.text} S'

            text_metrics += ' ) '

        logger.debug(text_metrics)

        for i in plugins.outputs:
            plugin = plugins.load(i)
            try:
                plugin.write(timestamp, metrics)
            except Exception as e:
                logger.exception("Error trying to write to %s: %s", plugin.plugin_name, str(e))


def main(argv):
    """
    Main appliction entry point
    """

    polling_interval = config.get("DEFAULT", "pollingInterval", fallback="* * * * *")
    debug_logging = False

    try:
        opts, _ = getopt.getopt(argv, "hdi:", ["help", "interval", "debug="])
    except getopt.GetoptError:
        print('evologger.py -h for help')
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print('evologger, version 2.0')
            print('')
            print('usage:  evologger.py [-h|--help] [-d|--debug <true|false>] [-i|--interval <interval>]')
            print('')
            print(' h|help                 : display this help page')
            print(' d|debug                : turn on debug logging, regardless of the config.ini setting')
            print(' i|interval <interval>  : This can be specified either in seconds, or as a cron-style string.')
            print('                          Option will override the config.ini value.')
            print(
                '                          If 0 is specified then only one run will complete, and the program will exit'
            )
            print('')
            sys.exit()
        elif opt in ('-i', '--interval'):
            polling_interval = str(arg)
        elif opt in ('-d', '--debug'):
            debug_logging = True

    configure_logging(logging.DEBUG if debug_logging or config.is_debugging_enabled('DEFAULT') else logging.INFO)

    logger.info("==Started==")

    global plugins
    sections = filter(lambda a: a.lower() != 'DEFAULT', config.sections())
    plugins = PluginLoader(config, sections, './plugins')
    scheduler = Scheduler(polling_interval)

    if polling_interval == '0':
        logger.info('One-off run, existing after a single publish')
    else:
        logger.info(f'Polling according to cron-style value of {polling_interval}')

    try:
        global continue_polling
        while continue_polling:
            publish_metrics(read_metrics())

            if polling_interval == '0':
                continue_polling = False
            else:
                sleep_duration = scheduler.time_until_next_run()
                if sleep_duration > 60:
                    logger.debug(f'Going to sleep for {(sleep_duration / 60):.2g} minutes')
                else:
                    logger.debug(f'Going to sleep for {sleep_duration:.2g} seconds')
                time.sleep(sleep_duration)

    except SystemExit:
        pass
    except Exception as e:
        logger.exception("An error occurred, trying again in 15 seconds: %s", str(e))
        time.sleep(15)

    logger.info("==Finished==")


if __name__ == '__main__':
    main(sys.argv[1:])
