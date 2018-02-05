from ftw.testbrowser import browsing
from ftw.testbrowser.pages import statusmessages
from opengever.testing import IntegrationTestCase


class TestSablonTemplateValidation(IntegrationTestCase):

    features = ('meeting', 'word-meeting')

    @browsing
    def test_invalid_template_is_rejected(self, browser):
        self.login(self.administrator, browser)
        browser.open(
            self.templates,
            view='++add++opengever.meeting.sablontemplate',
        )

        browser.fill({
            'Title': u'Sablonv\xferlage',
            'File': (
                'Sablon Template',
                'invalid_sablon_template.docx',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            ),
        }).save()
        self.assertEquals(['There were some errors.'],
                          statusmessages.error_messages())

    @browsing
    def test_valid_template_is_accepted(self, browser):
        self.login(self.administrator, browser)
        browser.open(
            self.templates,
            view='++add++opengever.meeting.sablontemplate',
        )

        browser.fill({
            'Title': u'Sablonv\xferlage',
            'File': (
                'Sablon Template',
                'sablon_template.docx',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            ),
        }).save()

        statusmessages.assert_no_error_messages()
