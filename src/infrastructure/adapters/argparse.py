import argparse
import os
from typing import Any


class EnvDefault(argparse.Action):
    # Credit: https://stackoverflow.com/a/10551190

    def __init__(
        self, env_var: str, required: bool = True, default: Any = None, **kwargs: Any
    ) -> None:
        if env_var and env_var in os.environ:
            default = os.environ[env_var]
        if required and default:
            required = False
        super(EnvDefault, self).__init__(default=default, required=required, **kwargs)

    def __call__(
        self, parser: Any, namespace: Any, values: Any, option_string: str | None = None
    ) -> None:
        setattr(namespace, self.dest, values)
