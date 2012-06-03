import logging

def configure(level='info', colored=False):
    '''
    Configure logging with custom format and optionally colorize it by
    special ANSI escape sequences
    '''

    # define const
    reset = "\033[0m"
    set_bold = "\033[1m"
    set_color = "\033[{0}m"
    black, red, green, yellow, blue, magenta, cyan, white = range(8)

    # set colors
    colors = {
        'INFO': green,
        'DEBUG': cyan,
        'ERROR': red,
        'WARNING': yellow,
        'CRITICAL': magenta,
        'NOTSET': blue
    }

    # define colorizer
    def add_colors(fn):
        def emit(*args):
            level = logging.getLevelName(args[1].levelno)
            color = 30 + colors.get(level)
            args[1].color = set_color.format(color)
            return fn(*args)
        return emit

    # change level
    log_level = getattr(logging, level.upper())

    # change format
    if colored:
        fmt = '{0}{1}[{2} {3}]{4}{0} {5}{4}'.format(
            '%(color)s', set_bold, '%(asctime)-15s',
            '%(levelname)s', reset, '%(message)s'
        )
        logging.StreamHandler.emit = add_colors(logging.StreamHandler.emit)
    else:
        fmt = '[%(asctime)-15s %(levelname)s] %(message)s'

    # configure
    config = {
        'level': log_level,
        'format': fmt,
        'datefmt': '%m-%d-%Y %H:%M:%S'
    }
    logging.basicConfig(**config)
