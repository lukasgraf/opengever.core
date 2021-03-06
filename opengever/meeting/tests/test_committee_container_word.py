from ftw.testbrowser import browsing
from ftw.testbrowser.pages import statusmessages
from opengever.testing import IntegrationTestCase
from ftw.testbrowser.pages import factoriesmenu


class TestCommitteeContainer(IntegrationTestCase):

    features = ('meeting',)

    @browsing
    def test_can_configure_ad_hoc_template(self, browser):
        self.login(self.administrator, browser)
        self.committee_container.ad_hoc_template = None

        self.assertIsNone(self.committee_container.ad_hoc_template)
        self.assertIsNone(self.committee_container.get_ad_hoc_template())

        browser.open(self.committee_container, view='edit')
        browser.fill({'Ad hoc agenda item template': self.proposal_template}).save()
        statusmessages.assert_no_error_messages()

        statusmessages.assert_message('Changes saved')

        self.assertIsNotNone(self.committee_container.ad_hoc_template)
        self.assertEqual(self.proposal_template,
                         self.committee_container.get_ad_hoc_template())

    @browsing
    def test_can_configure_paragraph_template(self, browser):
        self.login(self.administrator, browser)
        self.committee_container.paragraph_template = None

        self.assertIsNone(self.committee_container.paragraph_template)
        self.assertIsNone(self.committee_container.get_paragraph_template())

        browser.open(self.committee_container, view='edit')
        browser.fill({'Paragraph template': self.sablon_template}).save()
        statusmessages.assert_no_error_messages()

        statusmessages.assert_message('Changes saved')

        self.assertIsNotNone(self.committee_container.paragraph_template)
        self.assertEqual(self.sablon_template,
                         self.committee_container.get_paragraph_template())

    @browsing
    def test_can_add_with_templates(self, browser):
        self.login(self.manager, browser)
        browser.open()
        factoriesmenu.add('Committee Container')
        browser.fill({'Title': u'Sitzungen',
                      'Protocol header template': self.sablon_template,
                      'Protocol suffix template': self.sablon_template,
                      'Agenda item header template for the protocol': self.sablon_template,
                      'Agenda item suffix template for the protocol': self.sablon_template,
                      'Excerpt header template': self.sablon_template,
                      'Excerpt suffix template': self.sablon_template,
                      'Paragraph template': self.sablon_template,
                      'Ad hoc agenda item template': self.proposal_template}).save()
        statusmessages.assert_no_error_messages()

        self.assertEqual(self.proposal_template,
                         browser.context.get_ad_hoc_template())
        self.assertEqual(self.sablon_template,
                         browser.context.get_paragraph_template())
        self.assertEqual(self.sablon_template,
                         browser.context.get_excerpt_header_template())
        self.assertEqual(self.sablon_template,
                         browser.context.get_excerpt_suffix_template())

    @browsing
    def test_visible_fields_in_forms(self, browser):
        """Some fields should only be displayed when the word feature is
        enabled.
        Therefore we test the appearance of all fields.
        """
        fields = [u'Title',
                  u'Protocol header template',
                  u'Protocol suffix template',
                  u'Agenda item header template for the protocol',
                  u'Agenda item suffix template for the protocol',
                  u'Excerpt header template',
                  u'Excerpt suffix template',
                  u'Agendaitem list template',
                  u'Table of contents template',
                  u'Ad hoc agenda item template',
                  u'Paragraph template']
        self.login(self.manager, browser)

        browser.open()
        factoriesmenu.add('Committee Container')
        self.assertEquals(fields, browser.css('form#form > div.field > label').text)

        browser.open(self.committee_container, view='edit')
        self.assertEquals(fields, browser.css('form#form > div.field > label').text)
