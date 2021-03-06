from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browsing
from opengever.setup.casauth import install_cas_auth_plugin
from opengever.testing import FunctionalTestCase
from plone import api
import transaction


class TestLogoutOverlayWithoutCheckouts(FunctionalTestCase):

    def setUp(self):
        super(TestLogoutOverlayWithoutCheckouts, self).setUp()
        self.repo, self.repo_folder = create(Builder('repository_tree'))

        self.dossier = create(Builder('dossier').within(self.repo_folder))
        self.document = create(Builder("document").within(self.dossier))

    @browsing
    def test_logout_is_handled_using_a_js_script(self, browser):
        browser.login().open(view='logout_overlay')
        self.assertEquals(browser.contents, "empty:http://nohost/plone/logout")


class TestLogoutOverlayWithCheckouts(FunctionalTestCase):

    def setUp(self):
        super(TestLogoutOverlayWithCheckouts, self).setUp()
        self.repo, self.repo_folder = create(Builder('repository_tree'))
        self.dossier = create(Builder('dossier').within(self.repo_folder))

        self.checkout1 = create(
            Builder("document").titled("About Plone")
                               .within(self.dossier)
                               .checked_out())
        self.document = create(
            Builder("document").titled("NOT checkedout").within(self.dossier))
        self.checkout2 = create(
            Builder("document").titled("About Python")
                               .within(self.dossier)
                               .checked_out())

        transaction.commit()

    @browsing
    def test_contains_links_to_checked_out_documents(self, browser):
        browser.login().open(view='logout_overlay')
        checked_out_links = browser.css('.subContents li')
        self.assertEqual(2, len(checked_out_links))
        self.assertEqual(
            ['About Plone', 'About Python'],
            checked_out_links.text)

    @browsing
    def test_contains_hidden_field_with_redirect_url(self, browser):
        browser.login().open(view='logout_overlay')
        self.assertEqual(
            'http://nohost/plone/logout',
            browser.css('input[name="form.redirect.url"]').first.get('value'))


class TestLogoutOverlayWithCASAuth(FunctionalTestCase):

    def setUp(self):
        super(TestLogoutOverlayWithCASAuth, self).setUp()
        install_cas_auth_plugin()
        transaction.commit()

    def tearDown(self):
        super(TestLogoutOverlayWithCASAuth, self).tearDown()
        acl_users = api.portal.get_tool('acl_users')
        acl_users.plugins.removePluginById('cas_auth')
        transaction.commit()

    @browsing
    def test_redirects_to_cas_server_logout(self, browser):
        browser.login().open(view='logout_overlay')
        self.assertEquals('empty:http://example.com/portal/logout',
                          browser.contents)
