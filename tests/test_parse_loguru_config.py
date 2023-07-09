import json
import os
import sys
import io

import pytest
from loguru import logger
from loguru_config import LoguruConfig
from contextlib import redirect_stdout


@pytest.fixture(scope='function')
def temp_file():
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        yield f.name

    if os.path.exists(f.name):
        os.remove(f.name)


def test_normal_config():
    stream = io.StringIO()
    with redirect_stdout(stream) as f:
        logger.configure(
            handlers=[
                {
                    'sink': sys.stdout,
                    'format': '{level} - {message}',
                    'level': 'WARNING',
                },
            ])

        logger.info('Hello, world!')
        logger.critical('Hello, world!')

    assert stream.getvalue() == 'CRITICAL - Hello, world!\n'


def test_simple_config():
    stream = io.StringIO()
    with redirect_stdout(stream) as f:
        config = LoguruConfig(
            handlers=[
                {
                    'sink': 'ext://sys.stdout',
                    'format': '{level} - {message}',
                    'level': 'WARNING',
                },
            ])

        config.parse().configure()

        logger.info('Hello, world!')
        logger.critical('Hello, world!')

    assert stream.getvalue() == 'CRITICAL - Hello, world!\n'


def test_nested_config():
    stream = io.StringIO()
    with redirect_stdout(stream) as f:
        config = LoguruConfig(
            handlers=[
                {
                    'sink': 'ext://sys.stdout',
                    'format': '{level} - {message}',
                    'level': 'env://LOG_LEVEL',
                },
            ])

        os.environ['LOG_LEVEL'] = 'WARNING'

        config.parse().configure()

        logger.info('Hello, world!')
        logger.critical('Hello, world!')

    assert stream.getvalue() == 'CRITICAL - Hello, world!\n'


def test_nested_config_format_with_env():
    stream = io.StringIO()
    with redirect_stdout(stream) as f:
        config = LoguruConfig(
            handlers=[
                {
                    'sink': 'ext://sys.stdout',
                    'format': 'fmt://{{level}} - {env://NAME} - {{message}}',
                },
            ])

        os.environ['NAME'] = '[name]'

        config.parse().configure()

        logger.info('Hello, world!')

    assert stream.getvalue() == 'INFO - [name] - Hello, world!\n'


def test_user_defined_extra_format():
    stream = io.StringIO()
    with redirect_stdout(stream) as f:
        config = LoguruConfig(
            handlers=[
                {
                    'sink': 'ext://sys.stdout',
                    'format': '{level} - [start={extra[start_time]:%Y-%m-%d %H:%M:%S}] - {message}',
                },
            ],
            extra={
                'start_time': {
                    '()': 'datetime.datetime',
                    'year': 2020,
                    'month': 1,
                    'day': 1,
                }
            }
        )

        config.parse().configure()

        logger.info('Hello, world!')

    assert stream.getvalue() == 'INFO - [start=2020-01-01 00:00:00] - Hello, world!\n'


def test_user_defined_extra_repr():
    stream = io.StringIO()
    with redirect_stdout(stream) as f:
        config = LoguruConfig(
            handlers=[
                {
                    'sink': 'ext://sys.stdout',
                    'format': '{level} - [start={extra[start_time]!r}] - {message}',
                },
            ],
            extra={
                'start_time': {
                    '()': 'datetime.datetime',
                    'year': 2020,
                    'month': 1,
                    'day': 1,
                }
            }
        )

        config.parse().configure()

        logger.info('Hello, world!')

    assert stream.getvalue() == 'INFO - [start=datetime.datetime(2020, 1, 1, 0, 0)] - Hello, world!\n'


def test_user_defined_cfg():
    stream = io.StringIO()
    with redirect_stdout(stream) as f:
        config = LoguruConfig(
            extra={
                'start_time': {
                    '()': 'datetime.datetime',
                    'year': 2020,
                    'month': 1,
                    'day': 1,
                }
            },
            handlers=[
                {
                    'sink': 'ext://sys.stdout',
                    'format': 'fmt://{{level}} - [start={cfg://extra.start_time}] - {{message}}',
                },
            ],
        )

        config.parse().configure()

        logger.info('Hello, world!')

    assert stream.getvalue() == 'INFO - [start=2020-01-01 00:00:00] - Hello, world!\n'


def test_parse_level_from_environment_variable():
    stream = io.StringIO()
    with redirect_stdout(stream) as f:
        config = LoguruConfig(
            handlers=[
                {
                    'sink': 'ext://sys.stdout',
                    'format': '{level} ({level.icon}) - {message}',
                }],
            levels=[
                f'env://new_level',
            ]
        )

        os.environ['new_level'] = 'literal://{"name":"NEW", "no":13, "icon":"¤", "color":""}'

        config.parse().configure()

        logger.log('NEW', 'Hello, world!')

    assert stream.getvalue() == 'NEW (¤) - Hello, world!\n'


def test_parse_level_from_another_file(temp_file):
    stream = io.StringIO()
    with redirect_stdout(stream) as f:
        with open(temp_file, 'w') as f:
            json.dump({"name": "NEW2", "no": 14, "icon": "//¤//", "color": ""}, f)

        config = LoguruConfig(
            handlers=[
                {
                    'sink': 'ext://sys.stdout',
                    'format': '{level} ({level.icon}) - {message}',
                }],
            levels=[
                f'file://{temp_file}',
            ]
        )

        config.parse().configure()

        logger.log('NEW2', 'Hello, world!')

    assert stream.getvalue() == 'NEW2 (//¤//) - Hello, world!\n'


def test_loading_yaml_file(temp_file):
    json_contents = """
    {
  "handlers": [
    {
      "sink": "ext://sys.stderr",
      "format": "[{time}] {message}"
    },
    {
      "sink": "file.log",
      "enqueue": true,
      "serialize": true
    }
  ],
  "levels": [
    {
      "name": "NEW",
      "no": 13,
      "icon": "¤",
      "color": ""
    }
  ],
  "extra": {
    "common_to_all": "default"
  },
  "activation": [
    [
      "my_module.secret",
      false
    ],
    [
      "another_library.module",
      true
    ]
  ]
}
    """
    with open(temp_file, 'w') as f:
        f.write(json_contents)

    configurator = LoguruConfig.load(temp_file, configure=False).parse()

    expected_config = dict(
        handlers=[
            dict(sink=sys.stderr, format="[{time}] {message}"),
            dict(sink="file.log", enqueue=True, serialize=True),
        ],
        levels=[dict(name="NEW", no=13, icon="¤", color="")],
        extra={"common_to_all": "default"},
        activation=[["my_module.secret", False], ["another_library.module", True]],
    )

    assert configurator.handlers == expected_config['handlers']
    assert configurator.levels == expected_config['levels']
    assert configurator.extra == expected_config['extra']
    assert configurator.activation == expected_config['activation']
