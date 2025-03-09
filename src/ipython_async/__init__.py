"""IPython Async - Run cells asynchronously in IPython/Jupyter."""

__version__ = "0.1.0"

def load_ipython_extension(ipython):
    """Load the extension in IPython."""
    from .magics import AsyncMagics
    ipython.register_magics(AsyncMagics)