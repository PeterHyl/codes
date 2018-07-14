"""
:Module: basic_functions.py

:Author:
    Peter Hyl

:Description:
    This module contains only small functions which use only basic Python.
"""
import logging
import os
import shutil
import tempfile


def safe_func(func):
    """
    Simple decorator witch catches, logs and ignores all exceptions.
    Decorated function returns None, if any exception occurs.
    """

    def wrapped_func(*args, **kwargs):
        """ Calls above *func* and catch, log and ignore all exceptions.
        """
        try:
            return func(*args, **kwargs)
        except:  # (No exception type(s) specified) pylint: disable=W0702
            logging.debug("func={}, args={}, kwargs={}.".format(func, args, kwargs), exc_info=True)
            # send_mail()
            return None

    return wrapped_func


def new_path(path, iter_suffix=range(1000)):
    """
    Returns non-existing path with the lowest possible sufix.

    This is similar to what does Unix option *--backup-numbered* with *cp*.
    Moreover, this function can do it with any iterable (default are numbers).

    :Returns (str):
        path, if it does not exists.
        Otherwise, the first non-existing path (with the lowest suffix).

    :Raises:
        ValueError if paths with all possible suffixes exist.
    """
    if not os.path.exists(path):
        return path
    for suffix in iter_suffix:
        tmp_path = path + str(suffix)
        if not os.path.exists(tmp_path):
            return tmp_path
    raise ValueError("All possible paths exist!")


def initialize_logging(log_file, level):
    """
    Initialize logging into log_file with the logging level.
    """
    log_level = {"debug": logging.DEBUG, "info": logging.INFO, "warning": logging.WARNING, "error": logging.ERROR,
                 "critical": logging.CRITICAL}
    log_formatter = logging.Formatter("%(asctime)s %(threadName)-12s %(levelname)-5s  %(message)s")
    root_logger = logging.getLogger()

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(log_level[level.lower()])


def get_temp_file(dir=None):
    """
    Reserve file name in temp folder
    """
    (fd, temp_file) = tempfile.mkstemp(dir=dir)
    os.close(fd)
    return temp_file


def copy_to_temp(file, dir=None):
    """
    Copy file to temp and return temporary file name
    """
    temp_file = get_temp_file(dir=dir)
    shutil.copy(file, temp_file)
    return temp_file


def get_unc_path(path):
    """
    Returns UNC path
    """
    if not path:
        return None

    if os.name != "nt":
        return path

    path = os.path.abspath(path)
    if path.startswith("\\\\"):
        if path.startswith("\\\\?\\"):
            return path
        return "\\\\?\\UNC\\" + path[2:]
    else:
        return "\\\\?\\" + path


def remove_unc_prefix(path):
    """
    Returns path after removing \\\\?\\UNC\\ or \\\\?\\
    """
    if path.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path[8:]

    if path.startswith("\\\\?\\"):
        return path[4:]

    return path
