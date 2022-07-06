# Migas Client

A Python package to communicate with a migas server.

## API

`migas` includes the following functions to communicate with the telemetry server:

### migas.add_project()

Send a breadcrumb with usage information to the server.
The server will attempt to return information about the project,
such as the latest version and bad versions.

### migas.get_usage()

Check number of uses a `project` has received from a start date, and optionally an end date.
If no end date is specified, the current datetime is used.

## Customization

Normally, calling `migas.setup()` will populate the internal configuration with the default endpoint,
but in cases where you wish to host your own instance of a `migas` server,
you can pass in an `endpoint` parameter to route traffic accordingly.
