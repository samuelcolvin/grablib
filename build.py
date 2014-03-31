import os, re
    
print 'generating long_descriptions docs for PyPi...'
import pandoc
pandoc.core.PANDOC_PATH = '/usr/bin/pandoc'
doc = pandoc.Document()
readme_file = 'README.md'
doc.markdown = open(readme_file, 'r').read()
docs_file = 'GrabLib/docs.txt'
open(docs_file,'w').write(doc.rst)
print '%s converted to rst and written to %s' % (readme_file, docs_file)
print 'changing version number'
setup_text = open('setup.py','r').read()
s=re.search("version *= *'(.+?)'", setup_text)
v = s.groups()[0]
print 'setting version to: %s' % v
init_file = 'GrabLib/_version.py'
init_text = "__version__ = 'v%s'\n" % v
open(init_file,'w').write(init_text)