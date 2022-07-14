# Migas Client

A Python package to communicate with a migas server.

## About

`migas` (*mee-gahs*) is a Python client to facilitate communication with a [`migas` server](https://github.com/mgxd/migas-server).


## API

`migas` includes the following functions to communicate with the telemetry server:

### migas.add_project()

Send a breadcrumb with usage information to the server.
Usage information includes:
 - application
 - application version
 - python version
 - operating system
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


### migas.get_usage()

Check number of uses a `project` has received from a start date, and optionally an end date.
If no end date is specified, the current datetime is used.

<details>
<summary>get_usage example</summary>

```python
>>> get_usage('mgxd/migas-py', '2022-07-01')
{'hits': 7, 'message': '', 'unique': False}
```

</details>

## Customization

By default, `migas-py` will communicate with our hosted `migas server`, however it can easily be configured to communicate with any `migas server`.

To configure the client:

```python
import migas; migas.setup(endpoint='your-custom-endpoint-here', force=True)
```


### Environmental variables

To enable `migas`, you must have a non-empty environmental variable `ENABLE_MIGAS` set.
Additionally, you may control the request timeout by setting `MIGAS_TIMEOUT`.
