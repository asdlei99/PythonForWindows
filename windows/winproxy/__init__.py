print("Hello from winproxy")

from .apiproxy import (is_implemented,
                        get_target,
                        resolve)

from .error import WinproxyError
from .apis import * # Import all functions