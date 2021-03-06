from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browsing
from ftw.testbrowser import InsufficientPrivileges
from ftw.testbrowser.pages import factoriesmenu
from opengever.contact.interfaces import IContactSettings
from opengever.testing import add_languages
from opengever.testing import FunctionalTestCase
from opengever.testing import obj2brain
from plone import api
import transaction


class TestContact(FunctionalTestCase):

    def setUp(self):
        super(TestContact, self).setUp()
        self.grant('Member', 'Contributor', 'Manager')

        add_languages(['de-ch', 'fr-ch'])

    @browsing
    def test_add_a_contact(self, browser):
        contactfolder = create(Builder('contactfolder'))
        browser.login().open(contactfolder)
        factoriesmenu.add('Contact')
        browser.fill({'Firstname': 'Hanspeter',
                      'Lastname': 'D\xc3\xbcrr',
                      'Description': 'Lorem ipsum, bla bla'})
        browser.find('Save').click()

        self.assertEquals(
            'http://nohost/plone/opengever-contact-contactfolder/durr-hanspeter/contact_view',
            browser.url)
        self.assertEquals(u'D\xfcrr Hanspeter', browser.css('h1').first.text)

    @browsing
    def test_cannot_add_a_contact_with_contact_feature_enabled(self, browser):
        contactfolder = create(Builder('contactfolder'))

        browser.login().open(contactfolder)
        self.assertIn('Contact', factoriesmenu.addable_types())
        browser.visit(contactfolder, view="++add++opengever.contact.contact")

        api.portal.set_registry_record(
          'is_feature_enabled', True, interface=IContactSettings)
        transaction.commit()

        browser.open(contactfolder)
        self.assertNotIn('Contact', factoriesmenu.addable_types())
        with self.assertRaises(InsufficientPrivileges):
            browser.visit(contactfolder, view="++add++opengever.contact.contact")

    @browsing
    def test_edit_a_contact(self, browser):
        contactfolder = create(Builder('contactfolder'))
        contact = create(Builder('contact')
                         .within(contactfolder)
                         .having(firstname=u'Hanspeter',
                                 lastname='D\xc3\xbcrr'.decode('utf-8'),
                                 description=u'Lorem ipsum, bla bla'))

        browser.login().open(contact, view='edit')
        browser.fill({'Lastname': 'Walter'})
        browser.find('Save').click()

        self.assertEquals('Walter Hanspeter', browser.css('h1').first.text)

    def test_searchable_text(self):
        contact = create(Builder('contact')
                         .having(firstname=u'Hanspeter',
                                 lastname='D\xc3\xbcrr'.decode('utf-8'),
                                 description=u'Lorem ipsum, bla bla'))

        brain = obj2brain(contact)
        catalog = api.portal.get_tool('portal_catalog')
        data = catalog.getIndexDataForRID(brain.getRID())
        self.assertEquals(['durr', 'hanspeter'], data['SearchableText'])
