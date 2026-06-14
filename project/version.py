from importlib import metadata

try:
    __version__ = metadata.version('cmake_common')
except:
    __version__ = 'unknown'


def add_to_arg_parser(parser):
    parser.add_argument(
        '--version', '-V', action='version', version=f'%(prog)s {__version__}'
    )
