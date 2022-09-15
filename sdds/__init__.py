"""Exposes SddsFile, read_sdds and write_sdds directly in sdds namespace."""
from sdds.writer import write_sdds
from sdds.reader import read_sdds
from sdds.classes import SddsFile

__title__ = "sdds"
__description__ = "SDDS file handling."
__url__ = "https://github.com/pylhc/sdds"
__version__ = "0.3.1"
__author__ = "pylhc"
__author_email__ = "pylhc@github.com"
__license__ = "MIT"

# aliases
read = read_sdds
write = write_sdds


__all__ = [read, SddsFile, write, __version__]