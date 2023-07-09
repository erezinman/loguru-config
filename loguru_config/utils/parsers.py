import ast
import importlib
import sys
from typing import Any, Mapping, Union, Sequence, Callable, Optional
import os
import inspect


def parse_literal(literal: str) -> Any:
    """
    Parses a builtin value. The builtin value can be a string, an integer, a float, or a boolean. It can also be
    ``'stderr'`` or ``'stdout'`` to refer to the standard error and standard output streams, respectively. This
    function is useful for parsing string-only values (such as in environment variables).

    Examples
    --------
    >>> parse_literal('1')
    1

    >>> parse_literal('1.0')
    1.0

    >>> os.environ['TEST'] = 'True'
    >>> parse_literal(os.environ['TEST'])
    True

    Parameters
    ----------
    literal : str
         Either a python literal (such as an integer, float, boolean, `None`), or the builtins `stderr` & `stdout` (that
         refer to `sys.stderr` & `sys.stdout` respectively).

    Returns
    -------
    parsed: Any
        The parsed literal.
    """
    if literal == 'stderr':
        return sys.stderr
    if literal == 'stdout':
        return sys.stdout

    return ast.literal_eval(literal)


def parse_reference(reference_object: Union[Mapping, Sequence, Any], ref: str) -> Any:
    """
    References a part of an object using a string. The string is split on ``'.'`` and each part is used to index into
    the object.

    This function is similar to `cpython's ``logging.config.BaseConfigurator.cfg_convert``.

    Examples
    --------
    It is possible to reference a nested dictionary:
    >>> parse_reference({'a': {'b': {'c': 1}}}, 'a.b.c')
    1

    It is possible to reference a nested list:
    >>> parse_reference({'a': [{'b': 1}, {'b': 2}]}, 'a.1.b')
    2

    Also, in case of an integer, it can be parsed as an integer:
    >>> parse_reference({'a': {1: 1}}, 'a.1')
    1

    However, strings take precedence over integers:
    >>> parse_reference({'a': {1: 1, '1': '1'}}, 'a.1')
    '1'

    Also works with `__dict__`s of classes:
    >>> class A: a={'b': {'c': 1}}
    >>> parse_reference(A, 'a.b.c')
    1

    Note that in this example, `A` is used instead of `A()` because `a` is in the class's `__dict__`, not in the
    instance's `__dict__`.


    Parameters
    ----------
    reference_object: Union[Mapping, Sequence]
        The object to reference.

    ref: str
        The reference string. It is split on ``'.'`` and each part is used to index into the object.

    Returns
    -------
    parsed: Any
        The parsed reference.
    """

    current = reference_object
    rest = ref.split('.')

    while len(rest) > 0:
        ref, *rest = rest

        if isinstance(current, (list, tuple)):
            try:
                current = current[int(ref)]
            except ValueError:
                raise KeyError(f'Invalid reference: {ref!r}.')
        else:
            if not isinstance(current, Mapping):
                current = current.__dict__

            try:
                current = current[ref]
            except KeyError:
                if ref.isdigit():
                    current = current[int(ref)]
                else:
                    raise KeyError(f'Invalid reference: {ref!r}.')
    return current


def parse_external(external_ref: str) -> Any:
    """
    This function was copied shamelessly from cpython's ``logging.config.BaseConfigurator.ext_convert``.

    Resolve strings to objects using standard import and attribute syntax.

    Examples
    --------
    >>> parse_external('logging.handlers.RotatingFileHandler')
    <class 'logging.handlers.RotatingFileHandler'>

    >>> parse_external('sys.stdout')   # doctest: +SKIP
    <_io.TextIOWrapper name='<stderr>' mode='w' encoding='utf-8'>
    """
    name = external_ref.split('.')
    used = name.pop(0)
    try:
        found = importlib.import_module(used)
        for frag in name:
            used += '.' + frag
            try:
                found = getattr(found, frag)
            except AttributeError:
                importlib.import_module(used)
                found = getattr(found, frag)
        return found
    except ImportError as e:
        v = ValueError('Cannot resolve %r: %s' % (external_ref, e))
        raise v from e


_missing = object()


def parse_user_defined(user_defined_dict: dict,
                       further_parsing_function: Optional[Callable[[Any], Any]] = None) -> Any:
    """
    Parses a user defined function and calls it with the given arguments. The function is given as a dictionary with
    the following keys:
    - ``'()'``: The path (e.g. "package.subpackage.module") to call. This key is required.
    - ``'*'``: A list of positional arguments to pass to the function. This key is optional.
    - <key-word arguments>: The keys are the name of the arguments, and the values are the value of the argument. These
        keys are optional.

    This function is similar to the configuration syntax used by ``logging``, but extends it to allow for positional
    arguments.

    Examples
    --------
    >>> parse_user_defined({'()': 'sys.exc_info'})
    (None, None, None)

    >>> parse_user_defined({'()': 'datetime.date', 'year': 2020, 'month': 1, 'day': 1})
    datetime.date(2020, 1, 1)

    >>> parse_user_defined({'()': 'builtins.int', '*': ['123']})
    123

    >>> parse_user_defined({'()': 'builtins.str.format', '*': ['{} {world}', 'Hello'], 'world': 'World'})
    'Hello World'

    The ``further_parsing_function`` is called on each argument before calling the user-defined function:
    >>> parse_user_defined({'()': 'builtins.repr', '*': ["1"],})
    "'1'"
    >>> parse_user_defined({'()': 'builtins.repr', '*': ["1"],}, further_parsing_function=int)
    '1'

    Parameters
    ----------
    user_defined_dict: dict
        The dictionary to parse. See the description and the examples for the format.

    further_parsing_function: Optional[Callable[[Any], Any]]
        A function to apply to each value in the dictionary before calling the user-defined function. This is useful
        for parsing references and external references inside arguments.

    Returns
    -------
    parsed: Any
        The parsed user-defined function.
    """
    calling_function = user_defined_dict.pop('()', _missing)
    if calling_function is _missing:
        raise ValueError('User-defined handler must have a "()" key with the function to call.')

    calling_function = parse_external(calling_function)

    if not callable(calling_function):
        raise TypeError(f'User-defined handler must be callable, not {type(calling_function)!r}.')

    args = user_defined_dict.pop('*', ())
    if further_parsing_function is not None:
        user_defined_dict = {k: further_parsing_function(v) for k, v in user_defined_dict.items()}
        args = [further_parsing_function(arg) for arg in args]

    return calling_function(*args, **user_defined_dict)
