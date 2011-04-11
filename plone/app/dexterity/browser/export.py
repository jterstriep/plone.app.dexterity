# @@types-export view for dexterity types configlet. View support for the
# "Export" button. This is done by repurposing the GS typeinfo export and
# removing unselected type information from its output.

import time
from StringIO import StringIO
from zipfile import ZipFile
from elementtree import ElementTree

from Products.CMFCore.utils import getToolByName

from Products.Five.browser import BrowserView

from Products.GenericSetup.context import TarballExportContext, BaseContext


class SelectiveZipExportContext(TarballExportContext):

    def __init__(self, tool, typelist, encoding=None, base_name='setup_tool'):

        BaseContext.__init__(self, tool, encoding)

        self.typelist = typelist
        self.filenames = ['types.xml']
        for tn in typelist:
            self.filenames.append('types/%s.xml' % tn)

        timestamp = time.gmtime()
        self._archive_filename = (base_name + '-%4d%02d%02d%02d%02d%02d.zip'
                       % timestamp[:6])

        self._archive_stream = StringIO()
        self._archive = ZipFile(self._archive_stream, 'w')

    def writeDataFile(self, filename, text, content_type, subdir=None):
        if filename not in self.filenames:
            return

        if filename == 'types.xml':
            # Remove all the types except our targets.
            # Strategy: suck into ElementTree element, remove nodes,
            # convert back to text, prettify.
            root = ElementTree.fromstring(text)
            todelete = []
            for element in root.getchildren():
                name = element.attrib['name']
                if name != 'title' and name not in self.typelist:
                    todelete.append(element)
            for element in todelete:
                root.remove(element)
            # Add a marker for ZopeSkel additions
            root.append(ElementTree.Comment('-*- extra stuff goes here -*-'))
            # minor prettifying
            text = '<?xml version="1.0"?>\n%s' % ElementTree.tostring(root)
            text = text.replace('<!--', ' <!--')
            text = text.replace('-->', '-->\n')

        self._archive.writestr(filename, text)


class TypesExport(BrowserView):
    """Generate a types export archive for download
    """

    def __call__(self):
        RESPONSE = self.request.RESPONSE
        ps = getToolByName(self.context, 'portal_setup')

        items = self.request.selected.split(',')
        # context = SelectiveTarballExportContext(ps, items)
        context = SelectiveZipExportContext(ps, items,
          base_name='dexterity_export')
        handler = ps.getExportStep(u'typeinfo')
        message = handler(context)

        filename = context.getArchiveFilename()

        RESPONSE.setHeader('Content-type', 'application/zip')
        RESPONSE.setHeader('Content-disposition',
          'attachment; filename=%s' % filename)

        return context.getArchive()