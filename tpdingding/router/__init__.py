import glob
from importlib import import_module
from os.path import basename
from os.path import dirname
from os.path import isfile
from os.path import join
from pkgutil import walk_packages

from fastapi import APIRouter

router = APIRouter()


modules = glob.glob(join(dirname(__file__), "*.py"))
__all__ = [basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')]

for mod_info in walk_packages(__path__, f'{__name__}.'):
    import_module(mod_info.name)
