# Modern PyLogging

A library to simplify logging configuration.  

Inspired by `litestar`'s logging configuration.

[![Python Version](https://img.shields.io/pypi/pyversions/modern-pylogging.svg)](https://pypi.org/project/modern-pylogging/)
[![PyPI Version](https://img.shields.io/pypi/v/modern-pylogging.svg)](https://pypi.org/project/modern-pylogging/)
[![License](https://img.shields.io/github/license/wwarne/modern_pylogging.svg)](https://github.com/wwarne/modern_pylogging/blob/main/LICENSE)

## Overview

ModernPyLogging provides a wrapper around Python’s standard `logging` library,  
offering structured logging with JSON output, sensible defaults, and simplified configuration.

It is designed primarily for `async` applications and allows you to `bind` context so that every log entry contains it.

It implements the [recommended approach](https://docs.python.org/3.12/howto/logging-cookbook.html#dealing-with-handlers-that-block) to setting up loggers.

There are notable differences in the `logging` module between Python < 3.12 and >= 3.12  
(including a bug in 3.12.4 regarding the `queue` parameter in `QueueHandler`).

Due to these variations, I decided to extract my logging configuration into a reusable library for multiple projects.

## Features

- 🚀 **Simple API** – Get started with just a few lines of code  
- 🧱 **Built on the standard library** – Uses Python’s built-in logging module  
- 🔍 **Structured logging** – JSON output for easy parsing and analysis  
- 🎨 **Console output** – Human-readable logs during development  
- 🔧 **Flexible configuration** – Via code or configuration files  
- 🔄 **Tool integration** – Can use `orjson` and `picologging` if installed  
- 📊 **Context management** – Easily add context to your logs  

## Installation

```bash
pip install modern-pylogging
````

## Quick Start

```python
import modern_pylogging

config = modern_pylogging.LoggingConfig()
get_logger = config.configure()  # sets up logging and returns a logger getter (like logging.getLogger)

# Default logging level is INFO

# Get a logger for your module
logger = get_logger(__name__)

# Start logging!
logger.info("Application started")
logger.debug("Debug information", extra={"user_id": 12345})
logger.warning("Something might be wrong")
logger.error("An error occurred", exc_info=True)
```

## Default Configuration (Short Version)

* All logs are sent to `sys.stdout` (useful for Kubernetes or containers).
* All `filters`, `handlers`, etc., are attached to the root logger.
* `propagate` is not disabled – all logs from your app **and** external libraries are captured by the root logger.
* Default logging level is `INFO` (can be changed via the `LOGGING_LEVEL` env variable or manually).
* Logs are output in JSON format (Kubernetes-friendly).
* The environment (`env`, `system`, `inst`) is included in every log record, sourced from environment variables.
* `QueueHandler` is used to avoid blocking the main thread. It stores log records in a queue, and a corresponding
  `QueueListener` processes them separately (helpful for async event loops).
* If `orjson` is installed, it's used automatically for JSON dumping.
* If `picologging` is installed, it's used as a drop-in replacement for the standard `logging` module.
* Both `orjson` and `picologging` usage can be configured manually.

## Default Configuration (Extended Version)

```text
         MAIN THREAD             │      ANOTHER THREAD   
                                │                       
    APP─────┐                   │                       
           │                    │                       
           │                    │                       
     ┌─────▼──────────────────┐ │  ┌──────────────┐     
     │   Root logger          │ │  │QueueListener │     
     ├────────────────────────┤ │  └▲──────┬──────┘     
     │ Handler: QueueHandler  │ │   │      │            
     │                        │ │   │      │            
     └────┬───────────────────┘ │   │   ┌──▼─────────────┐       
          │                     │   │   │                │       
          │   ┌──────┐          │   │   │     STDOUT     │       
          └──►│QUEUE ├──────────┼───┘   └────────────────┘                
              └──────┘          │                       
                                │                       
```

### Differences Between Python ≤ 3.11 and ≥ 3.12

* **Python ≤ 3.11**: `QueueHandler` must have its own `Formatter` and sends pre-formatted data (usually `str`) to the queue.
  `QueueListener` simply passes them to its handlers (e.g., `stdout`). So the main thread performs all formatting and JSON serialization.

* **Python ≥ 3.12**: `QueueHandler` places `LogRecord` objects into the queue and must **not** have a `Formatter`.
  `QueueListener` receives raw `LogRecord`s and formats them in its own thread.

⚠️ Because of this, logging configs must differ depending on your Python version.

## Configuration

### Basic Configuration

The simplest way to configure logging:

```python
import modern_pylogging

# Configure with sensible defaults
config = modern_pylogging.LoggingConfig()
get_logger = config.configure()
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

`modern_pylogging.update_log_extra` allows you to bind context to the current coroutine.

This context propagates to all child coroutines created with `await`, `TaskGroup`, `create_task`, or `gather`.

Example:

If the name of parameter has a dot in it - it would be a nested dictionary in json output.

```python
import modern_pylogging

modern_pylogging.update_log_extra({
    'request.id': 'super ID',
    'request.method': 'GET',
})

logger.info('Done processing')
# Extra data is nested in JSON output:
# {'request': {'id': 'super ID', 'method': 'GET'}, ...}
```

All coroutines in the same `asyncio` Task share context (if you’re using `await`).
So nested coroutines can modify the shared context.

```python
import modern_pylogging

async def func_a():
    modern_pylogging.update_log_extra({'a': 'AAA'})
    await func_to_call()

async def func_to_call():
    modern_pylogging.update_log_extra({'b': 'BBB'})
```

Child tasks, however, run with a copy of the context and **cannot** change the parent’s context.
(Applies when using `asyncio.gather`, `create_task`, or `TaskGroup`.)

```python
from asyncio import TaskGroup
import modern_pylogging

async def func_a():
    modern_pylogging.update_log_extra({'a': 'AAA'})
    async with TaskGroup() as tg:
        tg.create_task(func_to_call())

async def func_to_call():
    modern_pylogging.update_log_extra({'b': 'BBB'})
```

### Logging Context Example

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
    logger.info('log from another_async_func')
    await asyncio.gather(task1(), task2())

async def task1():
    logger.info('log from task1')

async def task2():
    logger.info('log from task2')
```

**Expected Output:**

```json
{"message":"log from main"}
{"message":"log from main [updated]", "user_id":42}
{"message":"log from another_async_func", "user_id":42, "service":"k"}
{"message":"log from task1", "user_id":42, "service":"k"}
{"message":"log from task2", "user_id":42, "service":"k"}
{"message":"log after another_async_function", "user_id":42, "service":"k"}
```

## Overriding Formatters

During development, you may prefer string output instead of JSON in the console.
Instead of redefining the entire logger config, use the `override_formatters` parameter.

`queue_handler` sends data to `console` handler and depending on python version you're using
it's even queue_handler's Formatter or console's Formatter.

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
# Output (in dev mode):
>> 2025-05-09 20:24:08,888 | INFO | __main__:doc_file:13 | Application started |
```

## Configuring Existing Loggers

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
# All logs use DEBUG level, except specified loggers which remain at INFO.
```
