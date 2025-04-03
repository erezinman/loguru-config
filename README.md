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
other formats (again, see [Extending the configurator](#extending-the-configurator) below). Parsing formats other than
JSON depends on other packages, so you may specify the extras to automatically install packages necessary for parsing
the formats you specify.

## Installation

```bash
# Without extras (only supports JSON if other dependencies are not manually installed)
pip install loguru-config

# With extras (specify the formats you need other than JSON)
pip install loguru-config[json5, yaml, toml]
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

Use the following code to load your configuration from a file path string or a dictionary and apply to Loguru:

```python
from loguru_config import LoguruConfig

your_config_file_path_or_dict = "path/to/your/configuration_file.json"

LoguruConfig.load(your_config_file_path_or_dict)
```

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
  - [ "my_module.secret", false ]
  - [ "another_library.module", true ]
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

If you just want to get the configuration object instead of directly configuring Loguru, use the following code:

```python
from loguru_config import LoguruConfig

your_config_file_path_or_dict = "path/to/your/configuration_file.json"

config = LoguruConfig.load(your_config_file_path_or_dict, configure=False).parse()

# You may use or modify its attributes, or later manually call this to configure Loguru
config.configure()
```

## Special-case parsing

There are multiple special cases that are applicable. Some are recursive (i.e. after parsing, their contents will be
reparsed), and some aren't. The recursive cases will be marked as such in their header.

### String fields

1. `ext://` (recursive) - Load the member according to the reference after the prefix. This can be used, for example to
   refer to the application's out-streams (`ext://sys.stdout` or `ext://sys.stderr`), or to any loaded/loadable member
   in your own code (e.g. set the level of verbosity according to a predefined
   member `ext://my_package.utils.log_level`).
2. `cfg://` (recursive) - load a member from elsewhere in the configuration. This is similar to `ext://`, only within
   the configuration. For example, `cfg://handlers.0.level` will refer to the log-level in the first handler. The
   referencing supports both item-getting in dictionaries (`dict.key`), tuples and lists (`list.index`), and
   attribute-getting in other classes (uses the class' `__dict__` attribute).
3. `env://` (recursive) - load the field's value from an environmental variable. Since environmental-variables are only
   strings, `env://` fields can be combined (i.e. contain) `literal://` tags (more on these below). As an example use
   case, one can set an `extra` field to be the Windows username:
   ```yaml
   ...
   extra: 
      username: env://USERNAME
   ...
   ```
4. `literal://` - python-evaluate the contents of string following the prefix as literal python. For security reasons,
   the evaluation supports only simple built-in types (i.e. `int`, `float`, `str`, `bool`, `None` and lists,
   dictionaries, sets and tuples of these) without conditionals, assignments, lambda-expressions, etc. These are
   especially useful from loading string-only configurations (like `.ini` files), or mixed with `env://` for loading
   non-string values. Example: `"literal://True"` will evaluate to `True`
5. `fmt://` (recursive) - formats a string in an f-string-like way. This is useful to chain multiple variables. For
   example: `fmt://{env://APPDATA/}/{cfg://extra.name}/logs` evaluates to sub-folder of the application-data directory
   with the name given as the key `name` in the `extra` part.
   Some notes on this tag:
    - To escape curly braces, use double-curly braces (`{{` evaluates to `"{"`).
    - For now, specifying the individual formats of the formatted placeholders is not supported (e.g. one can not
      specify `"{number:.3f}"` because `:` is used in the tag prefixes). This might be resolved in the future.
6. `file://` (recursive) - for cases when you wish parts of the configuration to be shared among different
   configurations, one can do it using this tag. This tag loads the contents of the file (the same way the original file
   is loaded), and parses them to be inplace of the given tag. As an example, consider the case where multiple
   configurations have different `extra` section but similar handlers, the configuration might look like:
   ```yaml
   handlers: 'file://handlers.yaml'
   extra:
      ...
   ...
   ```

### Dictionary fields

7. The user-defined field, or `()`  (NON-RECURSIVE) - when declaring a user-defined field, one should have the contents
   of the field parse as a dictionary with the following keys:
    - `()`: parses as an `ext://` field above, but must refer to a callable.
    - `*` _(optional)_: this key's value, if such key is given, must be a list/tuple of positional arguments to pass to
      the function.
    - `<key>` _(optional)_: keyword-arguments to give the function.

   For example, one might wish to configure a `logging` handler as a sink:
   ```yaml
   handlers:
      - sink: 
          "()": logging.handlers.DatagramHandler
          "host": '127.0.0.1'
          "port": 3871
        level: ...
        ...
   ...
   ```

## Extending the configurator

Aside from inheriting the `LoguruConfig` class, there are two ways to extend the existing configurator class:

1. **Add a custom loading function** - by modifying the `LoguruConfig.supported_loaders` field. This field contains a
   list
   of callables that take a string (file name) as an argument and return a parsable object (i.e. a dictionary that can
   be passed as keyword-arguments to the `LoguruConfig` class' constructor). Note that the order of this list matters
   because the loaders will be attempted according to their order in the list.
2. **Add a custom string-field parser** - similarly, one can extend the class' parsing capabilities by
   extending `LoguruConfig.supported_protocol_parsers`. This field contains a list of tuples, where each tuple contains
   two elements:
    - Condition: can be either a callable taking a string and returning a boolean, or a regular expression. If the
      latter is given, then if the expression contains any groups, the first group will be passed to the parsing
      function.
    - Parsing function: a function that takes a string field and parses it.

As an example to the latter, consider the case where a special `eval` field can be given. In this case, one should
extend the configurator as follows:

```python
import re
from loguru_config import LoguruConfig

eval_protocol = re.compile(r'^eval://(.+)$')
LoguruConfig.supported_protocol_parsers = list(LoguruConfig.supported_protocol_parsers) + [
    (eval_protocol, eval)
]

LoguruConfig.load(...)
```

In contrast, one might not want affect all configurators - just one of them. In this case:

```python
import re
from loguru_config import LoguruConfig

eval_protocol = re.compile(r'^eval://(.+)$')
config = LoguruConfig.load(..., configure=False)

config.supported_protocol_parsers = list(LoguruConfig.supported_protocol_parsers) + [
    (eval_protocol, eval)
]

config.parse().configure()
```
