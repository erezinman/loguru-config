def load_toml_config(config_str: str) -> dict:
    import tomli
    return tomli.loads(config_str)


def load_json_config(config_str: str) -> dict:
    import json
    return json.loads(config_str)


def load_yaml_config(config_str: str) -> dict:
    import yaml
    return yaml.safe_load(config_str)


def load_json5_config(config_str: str) -> dict:
    import pyjson5
    return pyjson5.loads(config_str)
