import sys
from os import path

directory, file = path.split(__file__)
directory       = path.expanduser(directory)
directory       = path.abspath(directory)

sys.path.append(directory)