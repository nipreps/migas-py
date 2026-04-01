from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any

from migas.api.operations import _filter_response
from migas.config import Config, logger, telemetry_enabled
from migas.request import request


@dataclass
class Context:
    user_id: str | None = None
    session_id: str | None = None
    user_type: str | None = None
    platform: str | None = None
    container: str | None = None
    is_ci: bool | None = None


@dataclass
class Process:
    status: str | None = None
    status_desc: str | None = None
    error_type: str | None = None
    error_desc: str | None = None


@dataclass
class Breadcrumb:
    _route = '/api/breadcrumb'

    project: str
    project_version: str
    language: str | None = None
    language_version: str | None = None
    ctx: Context | None = None
    proc: Process | None = None

    @classmethod
    def from_config(cls, project: str, project_version: str, **kwargs) -> Breadcrumb:
        """Create a Breadcrumb instance using Config telemetry and user overrides."""
        # defaults - but kwargs take precedence
        data = Config.populate()
        data.update(kwargs)

        ctx = Context(
            user_id=data.get('user_id'),
            session_id=data.get('session_id'),
            user_type=data.get('user_type'),
            platform=data.get('platform'),
            container=data.get('container'),
            is_ci=data.get('is_ci'),
        )
        proc = Process(
            status=data.get('status'),
            status_desc=data.get('status_desc'),
            error_type=data.get('error_type'),
            error_desc=data.get('error_desc'),
        )

        return cls(
            project=project,
            project_version=project_version,
            language=data.get('language'),
            language_version=data.get('language_version'),
            # Only include nested objects if they have any data
            ctx=ctx if any(v is not None for v in asdict(ctx).values()) else None,
            proc=proc if any(v is not None for v in asdict(proc).values()) else None,
        )

    def to_dict(self) -> dict:
        """Convert to a nested dictionary, excluding None values."""
        return _recursive_filter_none(asdict(self))


def _recursive_filter_none(d: Any) -> Any:
    if isinstance(d, dict):
        return {k: _recursive_filter_none(v) for k, v in d.items() if v is not None}
    return d


@telemetry_enabled
def add_breadcrumb(
    project: str, project_version: str, wait: bool = False, **kwargs
) -> dict | None:
    """
    Send a breadcrumb with usage information to the telemetry server.

    Parameters
    ----------
    project : str
        Project name, formatted in GitHub `<owner>/<repo>` convention
    project_version : str
        Version string
    wait : bool, default=False
        If enabled, wait for server response.
    **kwargs
        Additional usage information to send. Includes:
        - `language`
        - `language_version`
        - `status`, `status_desc`, `error_type`, `error_desc`
        - `user_id`, `session_id`, `user_type`, `platform`, `container`, `is_ci`
    """
    payload = Breadcrumb.from_config(project, project_version, **kwargs).to_dict()
    logger.debug(payload)

    res = request(Config.endpoint, path=Breadcrumb._route, json_data=payload, wait=wait)
    if wait:
        logger.debug(res)
        return _filter_response(res[1], 'add_breadcrumb')
