# Migas Client

A Python package to communicate with a migas server.

## About

`migas` (*mee-gahs*) is a Python client to facilitate communication with a [`migas` server](https://github.com/mgxd/migas-server).


## Usage

To start communicating with a `migas` server, the client must first be setup.

```python
import migas; migas.setup()
```

By default, `migas-py` will communicate with the official hosted `migas` server.
However it can easily be configured to communicate with any hosted `migas` server.

```python
import migas; migas.setup(endpoint='your-endpoint')
```

`setup()` will populate the [interal configuration](#configuration), which is done at the process level.

### API

`migas` includes the following functions to communicate with the telemetry server:

#### migas.add_project()

Send a breadcrumb with usage information to the server.
Usage information includes:
 - application
 - application version
 - application status

The server will attempt to return version information about the project.

<details>
<summary>add_project example</summary>

```python
>>> add_project('mgxd/migas-py', '0.0.1')
{'bad_versions': [],
 'cached': True,
 'latest_version': '0.0.4',
 'message': '',
 'success': True}
```

</details>


#### migas.get_usage()

Check number of uses a `project` has received from a start date, and optionally an end date.
If no end date is specified, the current datetime is used.

<details>
<summary>get_usage example</summary>

```python
>>> get_usage('mgxd/migas-py', '2022-07-01')
{'hits': 7, 'message': '', 'unique': False, 'success': True}
```

</details>

## User Control

`migas` can controlled by the following environmental variables:

| Envvar | Description | Value | Default |
| ---- | ---- | ---- | ---- |
| MIGAS_OPTOUT | Disable telemetry collection | Any | None
| MIGAS_TIMEOUT | Seconds to wait for server response | Number >= 0 | 5
| MIGAS_LOG_LEVEL | Logger level | [Logging levels](https://docs.python.org/3/library/logging.html#levels) | WARNING


## Configuration

The internal configuration stores the following telemetry information:

- language and language version
- operating system
- run within a container
- run from continuous integration
