"""Eye of Thundera — sight beyond sight, for agents.

Point it at a running web app and it comes back with what a careful reviewer
would have noticed: broken images, console and network failures, horizontal
overflow, clipped text, misaligned rows, off-centre boxes, cramped tap targets,
failing contrast — across every screen size and theme you declare, with
screenshots and a machine-readable verdict.

    from thundera import Config, look
    result = look(Config.minimal("http://127.0.0.1:8000"))
    print(result.summary)

Extracted from the Vera Inspector, which was itself the third iteration of the
same idea. The engine is app-agnostic; everything app-specific lives in a
`thundera.toml`.
"""
from .api import LookResult, look, preflight
from .config import Config, ConfigError, Profile, Surface, Viewport

__version__ = "0.1.0"

__all__ = [
    "Config",
    "ConfigError",
    "LookResult",
    "Profile",
    "Surface",
    "Viewport",
    "look",
    "preflight",
    "__version__",
]
