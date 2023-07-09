import datetime
import sys
from importlib.util import find_spec

import pytest

from loguru_config import LoguruConfig
from loguru_config.parsable_config import literal_protocol, ext_protocol
from loguru_config.utils import parsers


# Most tests lie in the docs and should be called by doctest
def test_doctest():
    import doctest
    result = doctest.testmod(parsers, report=True, verbose=True)
    assert result.failed == 0, result.failed


@pytest.mark.parametrize('str_value,expected', [
    ('True', True),
    ('False', False),
    ('None', None),
    ('13', 13),
    ('3.14', 3.14),
    ('stderr', sys.stderr),
    ('stdout', sys.stdout),
    ('[1, 2, 3]', [1, 2, 3]),
    ("{'a': 1, 'b': 2}", {'a': 1, 'b': 2}),
    ("'a'", 'a'),
])
def test_literal_simple(str_value, expected):
    match = literal_protocol.match(f'literal://{str_value}')
    assert match is not None
    assert parsers.parse_literal(match.group(1)) == expected


@pytest.mark.parametrize('str_value,expected', [
    ('builtins.bool', bool),
    ('sys.stderr', sys.stderr),
    ('importlib.util.find_spec', find_spec),
    ('loguru_config.loguru_config.LoguruConfig', LoguruConfig),
])
def test_parse_external(str_value, expected):
    match = ext_protocol.match(f'ext://{str_value}')
    assert match is not None
    assert parsers.parse_external(match.group(1)) == expected
