"""
Create queries and mutations to be sent to the graphql endpoint.

Each etelemetry
"""
from functools import wraps
import os
import typing
from uuid import UUID

from .config import ETConfig as config, setup
from .request import request


class OperationTemplate(typing.TypedDict):
    operation: str
    args: dict


def telemetry_check(func: typing.Callable) -> typing.Callable:
    """Decorator function to ensure telemetry collection is enabled."""
    @wraps(func)
    def can_send(*args, **kwargs):
        if not os.getenv("ENABLE_ET", "0").lower() in ("1", "true", "y", "yes"):
            # do not communicate with server
            return {
                "success": False,
                "message": "eTelemetry is not enabled."
            }
        # otherwise, ensure config is set up
        setup()
        return func(*args, **kwargs)
    return can_send


fromDateRange: OperationTemplate = {
    'operation': 'query{fromDateRange($)}',
    'args': {
        # required
        'project': '"{}"',
        'start': '"{}"',
        # optional
        'end': '"{}"',
        'unique': '{}',
    }
}

@telemetry_check
def from_date_range(
    project: str,
    start: str,
    end: str = None,
    unique: bool = False,
) -> dict:
    params = _introspec(from_date_range, locals())
    query = _formulate_query(params, fromDateRange)
    _, _, body = request(config.endpoint, query)
    # TODO: Verify return is as expected
    return body


addProject: OperationTemplate = {
    'operation': 'mutation{addProject(p:{$})}',
    'args': {
        # required
        'project': '"{}"',
        'projectVersion': '"{}"',
        'language': '"{}"',
        'languageVersion': '"{}"',
        # optional
        'status': '{}',
        'user': '"{}"',
        'session': '"{}"',
        'container': '{}',
        'platform': '"{}"',
        'arguments': '"{}"',
    },
}

@telemetry_check
def add_project(
    project: str,
    projectVersion: str,
    language: str,
    languageVersion: str,
    userId: UUID = None,
    sessionId: UUID = None,
    container: str = None,
    platform: str = None,
    arguments: list = None,
) -> dict:
    # required:
    # owner, repo, version
    # language and language_version can be "assumed"
    #
    # extras:
    # - arguments (not yet implemented)
    # - container (unknown, docker, apptainer)
    # - platform (linux, darwin, etc)
    # - status (pending, success, fail)
    # - userID (uuid - we can generate this)
    # - sessionID (uuid - app will provide if they want)
    params = _introspec(add_project, locals())
    query = _formulate_query(params, addProject)
    _, _, body = request(config.endpoint, query)
    return body


def _introspec(func: typing.Callable, func_locals: dict) -> dict:
    """Inspect a function and return all set parameters."""
    import inspect

    sig = inspect.signature(func)
    return {
        param: func_locals[param] for param, val in sig.parameters.items()
        if func_locals[param] != val.default
    }


def _formulate_query(params: dict, template: OperationTemplate) -> str:
    """Construct the graphql query."""
    qparams = {x: template['args'][x].format(params[x]) for x in template['args'] if x in params}
    query = template['operation'].replace(
        "$", ",".join([f'{x}:{y}' for x, y in qparams.items()])
    )
    return query
