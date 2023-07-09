# Loguru-config

Loguru-config is a simple configurator for the [Loguru](https://github.com/Delgan/loguru) logging library. It extends
the functionality of Loguru by allowing the user to configure the logger from a configuration file. This package 
provides a much-needed feature to Loguru, which is the ability to configure the logger from a configuration file (for
example, using loguru alone, one can't automatically configure the logger to write to `sys.stdout` or `sys.stderr`
from within a configuration file).

The configuration can have syntax similar to the one used by the native `logging` library in Python (i.e. support
`cfg://`, `ext://`, etc.), but extends it to support even more features. It can also be easily extended to support even
more features quite easily (see [Extending the configurator](#extending-the-configurator) for more details).

The configurator supports parsing of JSON, JSON5, YAML, and TOML files (out of the box) and can be extended to support 
other formats (again, see [Extending the configurator](#extending-the-configurator) below).

## Installation

```bash
pip install loguru-config
```

## Features

- Supports parsing of JSON, YAML, and TOML files (out of the box) with a simple `Configurator.load` call.
- Supports loading a member of a module from a string (e.g. `ext://sys.stdout`).
- Support referencing another member of the configuration file (e.g. `cfg://loggers.default.handlers.0`).
- Support calling a user-defined function from within the configuration file (e.g. `{ '()': 'datetime.datetime.now' }`).
- Support referencing an environment variable (e.g. `env://HOME`).
- Support referencing (and parsing) referencing another file (e.g. `file://./path/to/file.json`).
- Support parsing literal python (strings, integers, lists, etc.) from within string values in a configuration (e.g.
  `literal://[1, 2, 3]`). 
- Support string formatting (e.g. `fmt://{cfg://loggers.default.handlers.0} - {{ESCAPED}}`).
- Also, almost all of these parsings are recursively parsed (except user-defined functions).
- Both the special-case parsing and configuration loading can be easily extended to support more features (see
  [Extending the configurator](#extending-the-configurator) below).

## Examples

The following YAML configuration file

```yaml
handlers:
    - sink: ext://sys.stderr
      format: '[{time}] {message}'
    - sink: file.log
      enqueue: true
      serialize: true
levels:
    - name: NEW
      'no': 13
      icon: ¤
      color: ""
extra:
    common_to_all: default
activation:
    - ["my_module.secret", false]
    - ["another_library.module", true]
```

will be parsed to  
```python
from loguru import logger
import sys

logger.configure(
    handlers=[
        dict(sink=sys.stderr, format="[{time}] {message}"),
        dict(sink="file.log", enqueue=True, serialize=True),
    ],
    levels=[dict(name="NEW", no=13, icon="¤", color="")],
    extra={"common_to_all": "default"},
    activation=[("my_module.secret", False), ("another_library.module", True)],
)
```

## Special-case parsing

...

## Extending the configurator

...