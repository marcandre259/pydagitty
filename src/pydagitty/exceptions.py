"""Exceptions raised by PyDagitty."""


class PyDagittyError(Exception):
    """Base class for package-specific errors."""


class InvalidGraphError(PyDagittyError):
    """Raised when a graph violates requirements of its declared type."""


class UnsupportedGraphTypeError(PyDagittyError):
    """Raised when an operation does not support the graph's declared type."""


class UnknownNodeError(PyDagittyError):
    """Raised when a node is not registered in a graph."""


class InvalidEdgeError(PyDagittyError):
    """Raised when an edge is malformed, stale, or incompatible with a graph."""
