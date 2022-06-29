"""
Create queries and mutations to be sent to the graphql endpoint.
"""
import sys
import typing
from uuid import UUID

from migas.config import Config, telemetry_enabled
from migas.request import request

if sys.version_info[:2] < (3, 8):
    from typing_extensions import TypedDict
else:
    from typing import TypedDict


class OperationTemplate(TypedDict):
    operation: str
    args: dict


fromDateRange: OperationTemplate = {
    "operation": "query{from_date_range($)}",
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
def from_date_range(
    project: str,
    start: str,
    end: str = None,
    unique: bool = False,
) -> dict:
    params = _introspec(from_date_range, locals())
    query = _formulate_query(params, fromDateRange)
    status, response = request(Config.endpoint, query)
    # TODO: Verify return is as expected
    return response


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
    language: str,
    language_version: str,
    userId: UUID = None,
    sessionId: UUID = None,
    container: str = None,
    platform: str = None,
    arguments: list = None,
) -> dict:
    params = _introspec(add_project, locals())
    query = _formulate_query(params, addProject)
    status, response = request(Config.endpoint, query)
    return status, response


def _introspec(func: typing.Callable, func_locals: dict) -> dict:
    """Inspect a function and return all set parameters."""
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
