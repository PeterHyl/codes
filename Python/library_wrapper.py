"""
:Module: library_wrapper.py

:Authors:
    Peter Hyl

:Description: Simple wrapper for library.
"""
import ctypes
import ctypes.util
import os


def _init():
    """
    Loads the library through ctypes and returns :class:`ctypes.CDLL`.
    """
    libpath = ctypes.util.find_library('lib_name') or os.path.join("path", "to", "library")
    if libpath:
        return ctypes.cdll.LoadLibrary(libpath)
    else:
        return None


def wrap_file_type_func(func):
    """
    Takes exported function from dll and returns correctly wrapped python function.
    """
    if os.name == "nt":
        func.restype = ctypes.c_int
        func.argtypes = [ctypes.c_wchar_p]
        return func
    else:
        func.restype = ctypes.c_ulong
        func.argtypes = [ctypes.c_char_p]
        return lambda x: func(x.encode())


_LIBRARY = _init()
if _LIBRARY:
    if hasattr(_LIBRARY, "function_from_lib"):
        function_from_lib = wrap_file_type_func(_LIBRARY.function_from_lib)
    if hasattr(_LIBRARY, "another_function"):
        another_function = wrap_file_type_func(_LIBRARY.another_function)
else:
    def function_from_lib(path):
        """
        Only raises exception.
        """
        raise ImportError("Library not found! ({} is irrelevant)".format(path))

    def another_function(path):
        """
        Only raises exception.
        """
        raise ImportError("Library not found! ({} is irrelevant)".format(path))
