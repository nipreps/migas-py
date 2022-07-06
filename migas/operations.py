"""
Create queries and mutations to be sent to the graphql endpoint.
"""
import sys
import typing
from uuid import UUID

from migas.config import Config, telemetry_enabled
from migas.request import request
from migas.utils import compile_info

if sys.version_info[:2] >= (3, 8):
    from typing import TypedDict
else:
    # TODO: 3.8 - Remove backport
    from typing_extensions import TypedDict


class OperationTemplate(TypedDict):
    operation: str
    args: dict


getUsage: OperationTemplate = {
    "operation": "query{get_usage($)}",
    "args": {
        # required
        "project": '"{}"',
        "start": '"{}"',
        # optional
        "end": '"{}"',
        "unique": "{}",
    },
}


@telemetry_enabled
def get_usage(
    project: str,
    start: str,
    end: str = None,
    unique: bool = False,
) -> dict:
    """

    `start` and `end` can be in either of the following formats:
        - YYYY-MM-DD
        - YYYY-MM-DDTHH:MM:SSZ

    """
    params = _introspec(get_usage, locals())
    query = _formulate_query(params, getUsage)
    status, response = request(Config.endpoint, query)
    # TODO: Verify return is as expected
    return status, response


addProject: OperationTemplate = {
    "operation": "mutation{add_project(p:{$})}",
    "args": {
        # required
        "project": '"{}"',
        "project_version": '"{}"',
        "language": '"{}"',
        "language_version": '"{}"',
        # optional
        "status": "{}",
        "user": '"{}"',
        "session": '"{}"',
        "container": "{}",
        "platform": '"{}"',
        "arguments": '"{}"',
    },
}


@telemetry_enabled
def add_project(
    project: str,
    project_version: str,
    language: str = None,
    language_version: str = None,
    user_id: UUID = None,
    session_id: UUID = None,
    container: str = None,
    platform: str = None,
    arguments: list = None,
) -> dict:
    parameters = _introspec(add_project, locals())
    # TODO: 3.9 - Replace with | operator
    params = {**compile_info(), **parameters}
    query = _formulate_query(params, addProject)
    status, response = request(Config.endpoint, query)
    # TODO: 3.10 - Replace with match/case

    # expected response:

    # {'data': {'add_project': {
    # 'bad_versions': [],
    # 'cached': False,
    # 'latest_version': '21.0.2',
    # 'message': '',
    # 'success': True}}}

    return status, response


def _introspec(func: typing.Callable, func_locals: dict) -> dict:
    """Inspect a function and return all parameters (not defaults)."""
    import inspect

    sig = inspect.signature(func)
    return {
        param: func_locals[param]
        for param, val in sig.parameters.items()
        if func_locals[param] != val.default
    }


def _formulate_query(params: dict, template: OperationTemplate) -> str:
    """Construct the graphql query."""
    qparams = {x: template["args"][x].format(params[x]) for x in template["args"] if x in params}
    query = template["operation"].replace("$", ",".join([f"{x}:{y}" for x, y in qparams.items()]))
    return query
