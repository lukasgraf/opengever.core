from Products.CMFCore.utils import getToolByName
from five import grok
from ftw.pdfgenerator.interfaces import IBuilder
from ftw.pdfgenerator.interfaces import ILaTeXLayout
from ftw.pdfgenerator.layout.makolayout import MakoLayoutBase
from opengever.ogds.base.utils import get_current_client
from zope.interface import Interface


class DefaultLayout(grok.MultiAdapter, MakoLayoutBase):
    """Opengever default layout.
    """
    grok.adapts(Interface, Interface, IBuilder)
    grok.provides(ILaTeXLayout)

    template_directories = ['resources']
    template_name = 'default_layout.tex'

    def __init__(self, context, request, builder):
        super(DefaultLayout, self).__init__(context, request, builder)
        self.show_contact = True
        self.show_logo = True
        self.show_organisation = False

        # XXX do not use zug specific default location in OG core.
        self.location = 'Zug'

    def before_render_hook(self):
        # XXX rename logo to logo.pdf
        self.add_raw_template_file('logo_sw.pdf')

        self.use_package('inputenc', options='utf8', append_options=False)
        self.use_package('ae,aecompl')
        self.use_package('babel', 'ngerman', append_options=False)
        self.use_package('fancyhdr')

        self.use_package('geometry', 'left=35mm')
        self.use_package('geometry', 'right=10mm')
        self.use_package('geometry', 'top=55mm')
        self.use_package('geometry', 'bottom=10.5mm')

        self.use_package('graphicx')
        self.use_package('lastpage')
        self.use_package('paralist', 'neveradjust', append_options=False)
        self.use_package('textcomp')

        self.use_package('textpos', 'absolute')
        self.use_package('textpos', 'overlay')
        self.use_package('titlesec', 'compact')
        self.use_package('wrapfig')
        self.use_package('array,supertabular')
        self.use_package('setspace')

    def get_render_arguments(self):
        owner = self.get_owner()
        owner_phone = owner.getProperty('phone_number', '&nbsp;')

        client = get_current_client()
        convert = self.get_converter().convert

        return {
            'client_title': convert(client.title),
            'member_phone': convert(owner_phone),
            'show_contact': self.show_contact,
            'show_logo': self.show_logo,
            'show_organisation': self.show_organisation,
            'location': self.location}

    def get_owner(self):
        mtool = getToolByName(self.context, 'portal_membership')
        creator_id = self.context.Creator()
        return mtool.getMemberById(creator_id)
