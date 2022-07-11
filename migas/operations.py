"""
Create queries and mutations to be sent to the graphql endpoint.
"""
import sys
import typing
from http.client import HTTPResponse
from uuid import UUID

from migas.config import Config, telemetry_enabled
from migas.request import request
from migas.utils import compile_info

if sys.version_info[:2] >= (3, 8):
    from typing import TypedDict
else:
    # TODO: 3.8 - Remove backport
    from typing_extensions import TypedDict


DEFAULT_ERROR = '[migas-py] An error occurred.'


class OperationTemplate(TypedDict):
    operation: str
    args: dict
    response: dict


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
    "response": {
        'success': False,
        'hits': 0,
        'message': DEFAULT_ERROR,
    },
}


@telemetry_enabled
def get_usage(
    project: str,
    start: str,
    end: str = None,
    # unique: bool = False,  # TODO: Add once supported in server
) -> dict:
    """
    Query project usage.

    This function requires a `project`, which is a string in the format of the GitHub
    `{owner}/{repository}`, and the start date to collect information.

    Additionally, an end date can be provided, or the current datetime will be used.

    `start` and `end` can be in either of the following formats:
        - YYYY-MM-DD
        - YYYY-MM-DDTHH:MM:SSZ

    Returns
    -------
    A dictionary containing the number of hits a project received.
    """
    params = _introspec(get_usage, locals())
    query = _formulate_query(params, getUsage)
    _, response = request(Config.endpoint, query)
    res = _filter_response(response, 'get_usage', getUsage["response"])
    return res


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
    "response": {
        'success': False,
        'message': DEFAULT_ERROR,
        'latest_version': None,
    },
}


@telemetry_enabled
def add_project(
    project: str,
    project_version: str,
    language: str = None,
    language_version: str = None,
    status: str = None,
    user_id: UUID = None,
    session_id: UUID = None,
    container: str = None,
    platform: str = None,
    arguments: list = None,
) -> dict:
    """
    Send project usage information to the telemetry server.

    This function requires a `project`, which is a string in the format of the GitHub
    `{owner}/{repository}`, and the current version of the software.

    Additionally, the follow information is collected:
    - language (python is assumed by default)
    - language version
    - platform
    - containerized (docker, apptainer/singularity)

    Returns
    -------
    A dictionary containing the latest released version of the project,
    as well as any messages sent by the developers.
    """
    parameters = _introspec(add_project, locals())
    # TODO: 3.9 - Replace with | operator
    params = {**compile_info(), **parameters}
    query = _formulate_query(params, addProject)
    _, response = request(Config.endpoint, query)
    res = _filter_response(response, 'add_project', addProject["response"])
    return res


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


def _filter_response(response: HTTPResponse, operation: str, fallback: dict):
    res = response.get("data")
    # success
    if isinstance(res, dict):
        return res.get(operation, fallback)

    # Otherwise data is None, return fallback response with error reported
    try:
        fallback['message'] = response.get('errors')[0]['message']
    finally:
        return fallback
