"""Support executing appharbor via `python3 -m appharbor`."""

import sys
from appharbor.main import main

if __name__ == "__main__":
    sys.exit(main())
