"""
Create queries and mutations to be sent to the graphql endpoint.
"""
import sys
import typing
from http.client import HTTPResponse

from migas.config import Config, logger, telemetry_enabled
from migas.request import request

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
    unique: bool = False,
) -> dict:
    """
    Query project usage.

    This function requires a `project`, which is a string in the format of the GitHub
    `{owner}/{repository}`, and the start date to collect information.

    Additionally, an end date can be provided, or the current datetime will be used.

    `start` and `end` can be in either of the following formats:
        - YYYY-MM-DD
        - YYYY-MM-DDTHH:MM:SSZ

    If `unique` is set to `True`, aggregates multiple uses by the same user as a single use.

    Returns
    -------
    A dictionary containing the number of hits a project received.
    """
    params = _introspec(get_usage, locals())
    query = _formulate_query(params, getUsage)
    logger.debug(query)
    _, response = request(Config.endpoint, query=query)
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
        "is_ci": '{}',
        # optional
        "status": "{}",
        "user_id": '"{}"',
        "session_id": '"{}"',
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
    **kwargs,
) -> dict:
    """
    Send project usage information to the telemetry server.

    This function requires a `project`, which is a string in the format of the GitHub
    `{owner}/{repository}`, and the current version being used.

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
    params = {**Config.populate(), **kwargs, **parameters}
    query = _formulate_query(params, addProject)
    logger.debug(query)
    _, response = request(Config.endpoint, query=query)
    res = _filter_response(response, 'add_project', addProject["response"])
    return res


def _introspec(func: typing.Callable, func_locals: dict) -> dict:
    """Inspect a function and return all parameters (not defaults)."""
    import inspect

    sig = inspect.signature(func)
    return {
        param: func_locals[param]
        for param, val in sig.parameters.items()
        if func_locals[param] != val.default and param != "kwargs"
    }


def _formulate_query(params: dict, template: OperationTemplate) -> str:
    """Construct the graphql query."""
    query_params = {}
    for template_arg in template["args"]:
        if template_arg in params:
            value = params[template_arg]
            if isinstance(value, bool):
                # booleans must be properly formatted
                value = str(value).lower()
            query_params[template_arg] = template["args"][template_arg].format(value)

    query = template["operation"].replace(
        "$", ",".join([f"{x}:{y}" for x, y in query_params.items()])
    )
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
