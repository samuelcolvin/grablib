#!/usr/bin/python
import sys, os
sys.path.append('..')
import GrabLib

class DummyArgs(object):
    target = None
    overwrite = True
    verbosity = None
    file_permissions = None
    def __init__(self, path):
        self.def_path = path

ex_dir = '../examples'
for file in sorted(os.listdir(ex_dir)):
    if not any([file.endswith(ext) for ext in ('.py', '.json')]):
        continue
    print('\n\n### Testing %s:\n' % file)
    args = DummyArgs(os.path.join(ex_dir, file))
    if not GrabLib.process_args(args):
        break