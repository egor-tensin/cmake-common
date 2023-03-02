try:
    import importlib.metadata as metadata
except ImportError:
    import importlib_metadata as metadata


try:
    __version__ = metadata.version('cmake_common')
except Exception:
    __version__ = 'unknown'


def add_to_arg_parser(parser):
    parser.add_argument('--version', '-V', action='version',
                        version=f'%(prog)s {__version__}')
