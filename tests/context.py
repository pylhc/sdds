import sys
from os.path import abspath, join, dirname, pardir
root_path = abspath(join(dirname(__file__), pardir, pardir))
if root_path not in sys.path:
    sys.path.insert(0, root_path)
tfs_path = join(root_path, "sdds")
if tfs_path not in sys.path:
    sys.path.insert(0, tfs_path)

import sdds