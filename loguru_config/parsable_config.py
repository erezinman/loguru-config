import copy
import pathlib
import re
import traceback
from typing import TYPE_CHECKING, Union, Optional, Callable, Pattern, Tuple, Collection, Type

from loguru_config.utils import parsers
import os
from loguru_config.utils.loaders import load_toml_config, load_json_config, load_yaml_config, load_json5_config

if TYPE_CHECKING:
    from typing_extensions import Self

try:
    PathLikeStr = os.PathLike[str]
except TypeError:
    PathLikeStr = os.PathLike

cfg_protocol = re.compile(r'^cfg://(.*)$')
word_regex = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*')

file_protocol = re.compile(r'^file://(.*)$')
literal_protocol = re.compile(r'^literal://(.*)$')
ext_protocol = re.compile(r'^ext://(.*)$')
env_var_protocol = re.compile(r'^env://(.*)$')

fmt_protocol = re.compile(r'^fmt://(.*)$')
format_value_regex = re.compile(r'(\{[^{}]+\}|[^{}]+)')


class ParsableConfiguration:
    """
    A configuration that can be parsed by the configuration loader. This class is used to load a configuration from a
    file or a dictionary, and then apply it to the logger.
    """

    __parsables__: Collection[str]
    """
    The names of the attributes that can be parsed by the configuration loader.
    """

    supported_protocol_parsers: Collection[Tuple[
        Union[Callable[[str], bool], Pattern],
        Callable[['ParsableConfiguration', str], str]
    ]]
    """
    The parsers that are supported by the configuration loader. The keys are the protocol parsers (either a callable
    that takes a string and returns a boolean, or a compiled regular expression); the values are the protocol parsers
    (callables that take a string and return a string).

    In case when a regex is used as a key, and the regex has a group, the group is used as the value to be passed to
    the protocol parser. Otherwise (a callable or no group in the regex), the entire string is passed to the protocol
    parser.
    """

    supported_loaders: Collection[Callable[[str], dict]] = [
        load_json_config,
        load_yaml_config,
        load_json5_config,
        load_toml_config
    ]

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.supported_loaders = list(self.supported_loaders)
        self.supported_protocol_parsers = list(self.supported_protocol_parsers)

    @classmethod
    def load(cls: Type['Self'], config_or_file: Union[PathLikeStr, dict], *, inplace: bool = False) -> Optional['Self']:
        """
        Load a configuration from a file or a dictionary.

        Parameters
        ----------
        config_or_file : Union[PathLikeStr, dict]
            The configuration to load. If a string, it is interpreted as a path to a file.
            If a dictionary, it is interpreted as a configuration dictionary.

        inplace : bool, default False
            Whether modifications to the configuration should be made in-place. If False, a copy of the configuration
            is made before modifications are made.

        Returns
        -------
        parsed: ParsableConfiguration
            The loaded Parsable

        """

        if isinstance(config_or_file, dict):
            if not inplace:
                config_or_file = copy.deepcopy(config_or_file)
        else:
            config_or_file = cls._load_from_file(config_or_file)
            if not isinstance(config_or_file, dict):
                raise TypeError(f'Config must be a dict, not {type(config_or_file)!r}.')

        return cls(**config_or_file)

    def parse(self) -> 'Self':
        """
        Parse the configuration. The parsed configuration is stored in the same object.
        """

        for key in self.__parsables__:
            value = getattr(self, key)
            if value is None:
                continue
            setattr(self, key, self._recursive_parse(value))

        return self

    @classmethod
    def _load_from_file(cls, file_path: PathLikeStr):

        with pathlib.Path(file_path).open('r') as f:
            file_contents = f.read()

        received_exceptions = {}
        for loader in cls.supported_loaders:
            try:
                return loader(file_contents)
            except ImportError:
                continue
            except Exception as e:
                received_exceptions[loader.__name__] = e
        else:
            # Arrived here without breaking, so no loader succeeded.
            formatted_exceptions = '\n'.join(
                f'  - {loader_name}: {"".join(traceback.format_exception(type(e), e, e.__traceback__))}'
                for loader_name, e in received_exceptions.items())
            raise SyntaxError(f'Could not load config file "{file_contents}" '
                              f'with any of the following loaders:\n{formatted_exceptions}')

    def _recursive_parse(self, element: Union[dict, list, tuple, str]):
        if isinstance(element, dict):
            if '()' in element:
                return parsers.parse_user_defined(element)
            return {k: self._recursive_parse(v) for k, v in element.items()}
        elif isinstance(element, (list, tuple)):
            tp = type(element)
            return tp(self._recursive_parse(v) for v in element)
        elif isinstance(element, str):
            return self._parse_string(element)
        else:
            return element

    def _parse_string(self, config_str: str):
        result = None
        for cond, handler in self.supported_protocol_parsers:
            if isinstance(cond, str):
                cond = re.compile(cond)
            if isinstance(cond, Pattern):
                match = cond.match(config_str)
                if match:
                    # Check if it has groups, then take the first. Otherwise, pass the original string.
                    if match.groups():
                        result = handler(self, match.group(1))
                    else:
                        result = handler(self, config_str)
            elif callable(cond):
                if cond(config_str):
                    result = handler(self, config_str)
            else:
                raise TypeError(f'Condition must be a regex, or callable, not {type(cond)!r}.')

            if result is not None:
                # Even though we just loaded it, we allow it to be parsed further (as a string).
                return self._recursive_parse(result)

        return config_str

    def _parse_log_part(self, file_path: PathLikeStr):
        loaded = self._load_from_file(file_path)
        return self._recursive_parse(loaded)

    def _parse_format(self, format_str: str):
        # Split by { and } to get the parts that are not inside curly braces.
        parts = format_value_regex.split(format_str)
        for i, part in enumerate(parts):
            if part.startswith('{') and part.endswith('}'):
                part = parts[i] = part[1:-1]
                if part.startswith('{') and part.endswith('}'):
                    # This is an escaped curly brace part, so we skip it.
                    parts[i] = part[1:-1]
                else:
                    # This is a curly brace part, so we need to parse it.
                    parts[i] = str(self._parse_string(parts[i]))

        return ''.join(parts)


ParsableConfiguration.supported_protocol_parsers = [
    (literal_protocol, lambda self, name: parsers.parse_literal(name)),
    (ext_protocol, lambda self, ref: parsers.parse_external(ref)),
    (env_var_protocol, lambda self, name: os.environ[name]),
    (file_protocol, ParsableConfiguration._parse_log_part),
    (cfg_protocol, parsers.parse_reference),
    (fmt_protocol, ParsableConfiguration._parse_format)
]
