import re
from types import TracebackType

from migas.error import strip_filenames

MAX_TRACEBACK_SIZE = 1500


def node_execution_error(etype: type, evalue: str, etb: TracebackType) -> dict:
    strpval = evalue.replace('\n', ' ').replace('\t', ' ').strip()
    node, tb = None, None

    if m := re.search(r'(?P<node>(?<=Exception raised while executing Node )\w+)', strpval):
        node = m.group('node').strip()

    if m := re.search(r'(?P<tb>(?<=Traceback:).*)', strpval):
        tb = strip_filenames(m.group('tb')).strip()
        # cap traceback size to avoid massive request
        if len(tb) > 1500:
            tb = f'{tb[:747]}...{tb[-750:]}'

    return {
        'status': 'F',
        'status_desc': f'Exception raised from node {node or "<?>"}',
        'error_type': 'NodeExecutionError',
        'error_desc': tb or 'No traceback available',
    }
