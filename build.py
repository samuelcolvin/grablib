
print 'generating long_descriptions docs for PyPi...'

import pandoc
pandoc.core.PANDOC_PATH = '/usr/bin/pandoc'
doc = pandoc.Document()

readme_file = 'README.md'
doc.markdown = open(readme_file, 'r').read()
rst_file = 'long_description.rst'
open(rst_file, 'w').write(doc.rst)

print '%s converted to rst and written to %s' % (readme_file, rst_file)
