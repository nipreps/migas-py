"""
Create queries and mutations to be sent to the graphql endpoint.
"""

from __future__ import annotations

import dataclasses
import enum
import json
import typing as ty

from migas.config import Config, logger, telemetry_enabled
from migas.request import request


class QueryParamType(enum.Enum):
    LITERAL = enum.auto()
    TEXT = enum.auto()


ERROR = '[migas-py] An error occurred.'


@dataclasses.dataclass
class Operation:
    operation_type: str
    operation_name: str
    query_args: dict
    selections: ty.Sequence[str] | None = None  # TODO: Add subfield selection support

    @classmethod
    def generate_query(cls, *args, **kwargs) -> str:
        parameters = _introspec(cls.generate_query, locals())
        params = {**kwargs, **parameters}
        query = cls._construct_query(params)
        return query

    @classmethod
    def _construct_query(cls, params: dict) -> str:
        """Construct the graphql query."""
        query_params = _parse_format_params(params, cls.query_args)
        query = f'{cls.operation_type}{{{cls.operation_name}({query_params})'
        if cls.selections:
            query += f'{{{",".join(f for f in cls.selections)}}}'
        query += '}'
        return query


@telemetry_enabled
def add_project(project: str, project_version: str, **kwargs) -> dict:
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
    # ...
    from .rest import add_breadcrumb

    return add_breadcrumb(project, project_version, wait=True, **kwargs)


class CheckProject(Operation):
    operation_type = 'query'
    operation_name = 'check_project'
    query_args = {
        'project': QueryParamType.TEXT,
        'project_version': QueryParamType.TEXT,
        'language': QueryParamType.TEXT,
        'language_version': QueryParamType.TEXT,
        'is_ci': QueryParamType.LITERAL,
        'status': QueryParamType.LITERAL,
        'status_desc': QueryParamType.TEXT,
        'error_type': QueryParamType.TEXT,
        'error_desc': QueryParamType.TEXT,
        'user_id': QueryParamType.TEXT,
        'session_id': QueryParamType.TEXT,
        'container': QueryParamType.LITERAL,
        'platform': QueryParamType.TEXT,
        'arguments': QueryParamType.TEXT,
    }
    selections = ('success', 'flagged', 'latest', 'message')


@telemetry_enabled
def check_project(project: str, project_version: str, **kwargs) -> dict:
    """
    Check a project version with the latest available.

    This can be used to check for the most recent version, as well as if
    the `project_version` has been flagged by developers.

    Returns
    -------
    response: dict
        keys: success, flagged, latest, message
    """
    query = CheckProject.generate_query(project=project, project_version=project_version, **kwargs)
    logger.debug(query)
    endpoint = f'{Config.endpoint.rstrip("/")}/graphql'
    _, response = request(endpoint, query=query, wait=True)
    logger.debug(response)
    res = _filter_response(response, CheckProject.operation_name)
    return res


class GetUsage(Operation):
    operation_type = 'query'
    operation_name = 'get_usage'
    query_args = {
        'project': QueryParamType.TEXT,
        'start': QueryParamType.TEXT,
        'end': QueryParamType.TEXT,
        'unique': QueryParamType.LITERAL,
    }


@telemetry_enabled
def get_usage(project: str, start: str, **kwargs) -> dict:
    """Retrieve usage statistics from the migas server.

    Parameters
    ----------
    project : str
        Project name, formatted in GitHub `<owner>/<repo>` convention
    start : str
        Start of data collection. Supports the following formats:
        `YYYY-MM-DD`
        `YYYY-MM-DDTHH:MM:SSZ'
    kwargs
        Additional arguments for the query
        end: End range of data collection. Same formats as `start`.
        unique: Filter out hits from same user_id.

    Returns
        response : dict
            success, hits, unique, message
    """
    query = GetUsage.generate_query(project=project, start=start, **kwargs)
    logger.debug(query)
    endpoint = f'{Config.endpoint.rstrip("/")}/graphql'
    _, response = request(endpoint, query=query, wait=True)
    logger.debug(response)
    res = _filter_response(response, GetUsage.operation_name)
    return res


def _introspec(func: ty.Callable, func_locals: dict) -> dict:
    """Inspect a function and return all parameters (not defaults)."""
    import inspect

    sig = inspect.signature(func)
    return {
        param: func_locals[param]
        for param, val in sig.parameters.items()
        if func_locals[param] != val.default and param != 'kwargs'
    }


def _filter_response(response: dict | str, operation: str, fallback: dict | None = None):
    if not fallback:
        fallback = {'success': False, 'message': ERROR}

    if isinstance(response, dict):
        if 'success' in response:
            return response

        res = response.get('data')
        # success
        if isinstance(res, dict):
            return res.get(operation, fallback)

    # Otherwise data is None, return fallback response with error reported
    try:
        if isinstance(response, dict) and response.get('errors'):
            fallback['message'] = response.get('errors')[0]['message']
        elif isinstance(response, dict) and response.get('detail'):
            fallback['message'] = response.get('detail')
    finally:
        return fallback


def _parse_format_params(params: dict, query_args: dict) -> str:
    query_inputs = []
    vals = None

    for qarg, qval in query_args.items():
        if qarg in params:
            val = params[qarg]
            if isinstance(val, bool):
                val = str(val).lower()

            if qval.name == 'TEXT':
                fval = json.dumps(val)
            elif qval.name == 'LITERAL':
                fval = val
            else:
                logger.error('Do not know how to handle type %s', qval.name)
                fval = ''
            query_inputs.append(f'{qarg}:{fval}')

        elif isinstance(qval, dict):
            vals = _parse_format_params(params, qval)
            query_inputs.append(f'{qarg}:{{{vals}}}')

    return ','.join(query_inputs)
