 from asyncio import TaskGroup

# Modern PyLogging

A library to simplify logging configuration. 

Inspired by `litestar` logging configuration.

[![Python Version](https://img.shields.io/pypi/pyversions/modern-pylogging.svg)](https://pypi.org/project/modern-pylogging/)
[![PyPI Version](https://img.shields.io/pypi/v/modern-pylogging.svg)](https://pypi.org/project/modern-pylogging/)
[![License](https://img.shields.io/github/license/wwarne/modern_pylogging.svg)](https://github.com/wwarne/modern_pylogging/blob/main/LICENSE)

## Overview

ModernPyLogging provides a wrapper around Python's standard logging library, 
offering structured logging with JSON output, sensible defaults, and simplified configuration.

It focuses more on `async` apps and allows you to `bind` some context so every log entry would contain it.

It implements [recommended way](https://docs.python.org/3.12/howto/logging-cookbook.html#dealing-with-handlers-that-block) of setting up loggers.

There are some changes in `logging` module between Python < 3.12 and Python >= 3.12 
(and even a bug in 3.12.4 regarding `queue` parameter for QueueHandler).

Because of all this I decided to put my logging config in a library to re-use it among different projects.


## Features

- 🚀 **Simple API** - Get started with just a few lines of code
- 🧱 **Built on standard library** - Uses Python's built-in logging module under the hood
- 🔍 **Structured logging** - JSON output for easy parsing and analysis
- 🎨 **Pretty console output** - Human-readable logs during development
- 🔧 **Flexible configuration** - Through code or configuration files
- 🔄 **Integration with other tools** - could use `orjson` and `picologging` if installed
- 📊 **Context management** - Add context to your logs easily


## Installation

```bash
pip install modern-pylogging
```

## Quick Start

```python
import modern_pylogging

config = modern_pylogging.LoggingConfig()
get_logger = config.configure() # this will setup logging and return a function to get a logger like logging.getLogger
# default logging level is INFO
# Get a logger for your module
logger = get_logger(__name__)

# Start logging!
logger.info("Application started")
logger.debug("Debug information", extra={"user_id": 12345})
logger.warning("Something might be wrong")
logger.error("An error occurred", exc_info=True)
```

## Default configuration (short version)

- All logs output in `sys.stdout`. (Helps with k8s/running inside containers)
- All `filters`, `handlers`, etc... are in `root` logger
- `Proragate` does not turned off - so every log record from my app AND from other used libraries would be captured by `root` logger.
- Default logging level is `INFO`. (Could be changed with LOGGING_LEVEL env variable or manually)
- Logs output in JSON format. (Helps with k8s)
- I log `env`, `system`, `inst` with every logRecord. Values are taken from env variables.  (Helps with k8s)
- I use `QueueHandler` to log off the main thread. `queue_handler` stores all logRecords in a queue and assosiated
`QueueListener` accepts those records and processes them. (it helps not to block main thread therefore async eventloop)
- If you have `orjson` installed - it will be used automatically for dumping json.
- If you have `picologging` installed - it will be used automatically instead of stdlib `logging`
- Using `orjson` and `picologging` could be configured by hand.

## Default configuration (extended version)


                                                       
          MAIN THREAD          │      ANOTHER THREAD   
                               │                       
    APP─────┐                  │                       
            │                  │                       
            │                  │                       
     ┌──────▼─────────────────┐│  ┌──────────────┐     
     │   Root logger          ││  │QueueListener │     
     ├────────────────────────┤│  └▲──────┬──────┘     
     │ Handler "QueueHandler  ││   │      │            
     │                        ││   │      │            
     └──────┬─────────────────┘│   │   ┌──▼─────────────┐       
            │                  │   │   │                │       
            │   ┌──────┐       │   │   │     STDOUT     │       
            └──►│QUEUE ├───────┼───┘   └────────────────┘                
                └──────┘       │                       
                               │                       

### Difference between python <= 3.11 and 3.12

- python <= 3.11 - QueueHandler must have its own `Formatter` and it puts in `Queue` already processed record (usually its a `str`). 
Then `QueueListener` just passes it to its `Handlers` (in my case it's only stdout output). So all the work of constructing and formatting
log record + converting it into JSON is happening right in main thread.
- python >= 3.12 - QueueHandler puts objects of a `LogRecord` class in `Queue`. It must not have any Formatter
(to prevent the duplicate work). `QueueListener` gets `LogRecord` instances and formats them in its own thread.

Because of that you need the different logging configs based on your Python version.
                 

## Configuration

### Basic Configuration

The simplest way to configure logging:

```python
import modern_pylogging

# Configure with sensible defaults
config = modern_pylogging.LoggingConfig(
    logging_module='logging',
    level='INFO',
    ...
)
```

Parameters of LoggingConfig:

`logging_module (Literal['logging', 'picologging']):`

Specifies the backend logging module to use. 'logging' is the standard library,
while 'picologging' is a faster, drop-in replacement.
'picologging' will be used by default if installed.

`json_dumps_module (Literal['json', 'orjson']):`

Module used to serialize log records to JSON format. 'orjson' provides better
performance and type handling. 'orjson' will be used by default if installed.

`version (Literal[1]):`

Schema version for the logging configuration.
The only valid value at present is 1

`disable_existing_loggers (bool):`

Whether to disable loggers that were previously configured before applying this config.

`filters (dict[str, dict[str, Any]] | None):`

A dict in which each key is a filter id and each value is a dict describing how to configure the
corresponding Filter instance.
https://docs.python.org/3/library/logging.html#filter-objects.

`formatters (dict[str, dict[str, Any]] | None):`

A dict in which each key is a formatter and each value is a dict describing how to configure the
corresponding Formatter instance. A 'standard' and 'json_fmt' formatter is provided.
standard - write everything as strings, good for development.
json_fmt - write output as json, good for production.
https://docs.python.org/3/library/logging.html#formatter-objects

`handlers (dict[str, dict[str, Any]] | None):`

A dict in which each key is a handler id and each value is a dict describing how to configure the
corresponding Handler_ instance. Two handlers are provided, 'console' and 'queue_handler'.
https://docs.python.org/3/library/logging.html#handler-objects

`loggers (dict[str, dict[str, Any]] | None):`

A dict in which each key is a logger name and each value is a dict describing how to configure the
corresponding Logger_ instance.
https://docs.python.org/3/library/logging.html#logger-objects

`root (dict[str, dict[str, Any] | list[Any] | str] | None):`

This will be the configuration for the root logger.
Processing of the configuration will be as for any logger,
except that the propagate setting will not be applicable.

`override_formatters (dict[HandlerName, FormatterName] | None):`

Sometimes you want just use default settings but change formatters
(e.g. to write to console as text instead of json)
You could provide a dict like {'console': 'standard', 'queue_handler': 'standard'}

`level (int | str | None):`

Optional default logging level to be applied globally (e.g., 'DEBUG', 10).

`capture_extra_fields (bool):`

Whether to capture additional fields from log records' `extra` parameter
into the structured output (especially relevant for JSON loggers).
This does not work for 'picologging'.
It's where you use like this - logger.info('abc', extra={'key': 'value'})



## Context Management

`modern_pylogging.update_log_extra` allows you to save context related to current async coroutine.

Such context would be available to all "child" coroutines which are created via `await`, `TaskGroup`, `create_task`, `gather`.

For example - in the beginning of request processing Middleware could use `modern_pylogging.update_log_extra` to set 
`request_id`. And every log message would contain this `request_id`, which helps tremendously later than you're filtering logs. 

If the name of parameter has a dot in it - it would be a nested dictionary in json output.

Example

```python
import modern_pylogging

modern_pylogging.update_log_extra({
    'request.id': 'super ID',
    'request.method': 'GET',
})
...
logger.info('Done processing')
# the extra data would be converted as
{'request': {'id': 'super ID', 'method': 'GET'}, other log fields}
```

Extra fields are automatically added in JSONFormatter.

All coroutines inside one asyncio Task are running in one context
(if you are await something for example). So such coroutines could change "parent" context.

```python
import modern_pylogging

async def func_a():
    # now context is empty
    modern_pylogging.update_log_extra({'a': 'AAA'})
    # now context is {'a': 'AAA'}
    await func_to_call()
    # now context is {'a': 'AAA', 'b': 'BBB'}

async def func_to_call():
    # called from func_a - shared context {'a': 'AAA'}
    modern_pylogging.update_log_extra({'b': 'BBB'})
    # now context is {'a': 'AAA', 'b': 'BBB'}
```


Child tasks running with a copy of context and can't change parent's context.
(child tasks are created when you use asyncio.gather, create_task, or TaskGroup)

```python
from asyncio import TaskGroup
import modern_pylogging


async def func_a():
    # now context is empty
    modern_pylogging.update_log_extra({'a': 'AAA'})
    # now context is {'a': 'AAA'}
    async with TaskGroup() as tg:
        # we could use .gather here too -
        tg.create_task(func_to_call())
    # now context is {'a': 'AAA'} (taskgroup call had a copy and could not change parents contextvar)

async def func_to_call():
    # called from func_a but because it's another Task, we have a COPY of context {'a': 'AAA'}
    modern_pylogging.update_log_extra({'b': 'BBB'})
    # now context is {'a': 'AAA', 'b': 'BBB'}
```

Example with logs

```python
import asyncio
import modern_pylogging
import logging

modern_pylogging.LoggingConfig(logging_module='logging').configure()

logger = logging.getLogger('example')


async def main():
    logger.info('log from main')
    modern_pylogging.update_log_extra({'user_id': 42})
    logger.info('log from main [updated]')
    await another_async_func()
    logger.info('log after another_async_function')


async def another_async_func():
    modern_pylogging.update_log_extra({'service': 'k'})
    logger.info('log from another_async_func')  # would have user_id from parent task + service parameter
    tasks = [task1(), task2()]
    await asyncio.gather(*tasks)
    
async def task1():
    logger.info('log from task1')

async def task2():
    logger.info('log from task2')

# Output is going to be like this
{"message":"log from main",}
{"message":"log from main [updated]", "user_id":42}
{"message":"log from another_async_func","user_id":42,"service":"k"}
{"message":"log from task1","user_id":42,"service":"k"}
{"message":"log from task2","user_id":42,"service":"k"}
{"message":"log after another_async_function","user_id":42,"service":"k"}
```

### Override formatters

During development I want my logs to be just strings without cluttering my console with huge jsons.

But I don't want to override all configuration for loggers and formatters just to change output from json to string.

So I created parameter `override_formatters` which just replaces one formatter to another 

We have `standard` formatter and `json_dmp` formatter and two handlers `console` and `queue_handler`

`queue_handler` sends data to `console` handler which and depending on python version you're using
it's even queue_handler's Formatter or console's Formatter. So I just override them both

```python
import logging
import os

import modern_pylogging

if os.environ.get('DEV_MODE'):
    override_formatters = {'queue_handler': 'standard', 'console': 'standard'}
else:
    override_formatters = {}

modern_pylogging.LoggingConfig(logging_module='logging', override_formatters=override_formatters).configure()

logger = logging.getLogger('example')

logger.info("Application started")
# Output
>> 2025-05-09 20:24:08,888 | INFO | __main__:doc_file:13 | Application started |
```

And now I have console output in dev mode

## Configuring existing loggers

```python
import modern_pylogging

config = modern_pylogging.LoggingConfig(
    logging_module='logging',
    level='DEBUG',
    loggers={
        'httpx': {'handlers': [], 'level': 'INFO', 'propagate': True},
        'peewee': {'handlers': [], 'level': 'INFO', 'propagate': True},
        'aiokafka': {'handlers': [], 'level': 'INFO', 'propagate': True},
    }
)
config.configure()
# As a result - every logging would be with DEBUG level but specified loggers would stay with INFO level

```

## Default configs

Default config for `logging` and Python <= 3.11
```python
{
    'version': 1, 
    'formatters': {
        'standard': {
            '()': 'modern_pylogging.console_formatter.ConsoleFormatterLogging',
            'format': '%(asctime)s | %(levelname)s | %(name)s:%(module)s:%(lineno)s | %(message)s | %(extra_data_str)s'
        },
        'json_fmt': {
            '()': 'modern_pylogging.json_formatter.JsonFormatterLogging',
            'json_dumps_module': 'json',
            'capture_extra_fields': False
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json_fmt',
            'stream': 'ext://sys.stdout'
        },
        'queue_handler': {
            'class': 'modern_pylogging.logging_handlers.QueueListenerHandler',
            'formatter': 'json_fmt',
            'respect_handler_level': True
        }
    },
    'root': {
        'handlers': ['queue_handler'],
        'level': 'INFO'
    }
}
```

Default config for `logging` and Python >= 3.12

```python
{
    'version': 1,
    'formatters': {
        'standard': {
            '()': 'modern_pylogging.console_formatter.ConsoleFormatterLogging',
            'format': '%(asctime)s | %(levelname)s | %(name)s:%(module)s:%(lineno)s | %(message)s | %(extra_data_str)s'
        },
        'json_fmt': {
            '()': 'modern_pylogging.json_formatter.JsonFormatterLogging',
            'json_dumps_module': 'json',
            'capture_extra_fields': False
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json_fmt',
            'stream': 'ext://sys.stdout'
        },
        'queue_handler': {
            'class': 'modern_pylogging.logging_handlers.QueueHandlerContextVarsHappyPy312',
            'respect_handler_level': True,
            'queue': {
                '()': 'queue.Queue',
                'maxsize': -1
            },
            'listener': 'modern_pylogging.logging_handlers.LoggingQueueListener',
            'handlers': ['console']
        }
    },
    'root': {
        'handlers': ['queue_handler'],
        'level': 'INFO'
    }
}
```

Default `picologging` config

```python
{
    'version': 1,
    'formatters': {
        'standard': {
            '()': 'modern_pylogging.console_formatter.ConsoleFormatterPicologging',
                                           'format': '%(asctime)s | %(levelname)s | %(name)s:%(module)s:%(lineno)s | %(message)s | %(extra_data_str)s',
                                           'datefmt': '%F %T'},
                              'json_fmt': {'()': 'modern_pylogging.json_formatter.JsonFormatterPicologging',
                                           'json_dumps_module': 'json', 'capture_extra_fields': False}}, 'handlers': {
    'console': {'class': 'modern_pylogging.picologging_handlers.PicoStreamHandlerToStdout', 'formatter': 'json_fmt',
                'stream': 'ext://sys.stdout'},
    'queue_handler': {'class': 'modern_pylogging.picologging_handlers.QueueListenerHandler', 'formatter': 'json_fmt'}},
 'root': {'handlers': ['queue_handler'], 'level': 'INFO'}}
```


## License

This project is licensed under the MIT License - see the LICENSE file for details.
