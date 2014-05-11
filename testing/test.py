#!/usr/bin/python
import sys, os
sys.path.append('..')
import GrabLib

class DummyArgs(object):
    libs_root = None
    overwrite = True
    verbosity = None
    file_permissions = None
    def __init__(self, path):
        self.def_path = path
        
def test_file(path):
    print('\n\n### Testing %s:\n' % path)
    args = DummyArgs(path)
    return GrabLib.process_args(args)

if len(sys.argv) > 1:
    path = sys.argv[-1]
    test_file(path)
else:
    ex_dir = '../examples'
    for file in sorted(os.listdir(ex_dir)):
        if not any([file.endswith(ext) for ext in ('.py', '.json')]):
            continue
        path = os.path.join(ex_dir, file)
        if not test_file(path):
            break