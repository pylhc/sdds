import sys
from os.path import abspath, join, dirname, pardir
root_path = abspath(join(dirname(__file__), pardir))
if root_path not in sys.path:
    sys.path.insert(0, root_path)
import sdds
