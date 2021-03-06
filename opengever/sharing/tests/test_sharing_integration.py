from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browsing
from opengever.ogds.base.utils import get_current_org_unit
from opengever.sharing.browser.sharing import OpengeverSharingView
from opengever.sharing.browser.sharing import SharingTab
from opengever.sharing.interfaces import ILocalRolesAcquisitionActivated
from opengever.sharing.interfaces import ILocalRolesAcquisitionBlocked
from opengever.sharing.interfaces import ILocalRolesModified
from opengever.testing import FunctionalTestCase
from opengever.testing import IntegrationTestCase
from opengever.testing.event_recorder import get_last_recorded_event
from opengever.testing.event_recorder import register_event_recorder
from opengever.testing.pages import tabbedview
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME


class TestOpengeverSharingIntegration(FunctionalTestCase):
    use_default_fixture = False

    def setUp(self):
        """ Set up test environment
        """
        super(TestOpengeverSharingIntegration, self).setUp()
        self.grant('Manager')
        create(Builder('fixture').with_admin_unit())
        self.repo = create(Builder("repository"))
        self.dossier = create(Builder("dossier").within(self.repo))

        self.view_repo = OpengeverSharingView(self.repo, self.portal.REQUEST)
        self.view_dossier = OpengeverSharingView(self.dossier, self.portal.REQUEST)
        self.tab_dossier = SharingTab(self.dossier, self.portal.REQUEST)

    def _check_roles(self, expected, roles):
        """ Base method to check the received roles
        """
        self.assertItemsEqual(expected, [role['id'] for role in roles])

        # Reset the roles
        setRoles(
            self.portal, TEST_USER_ID, ['Manager', 'Contributor', 'Editor'])

    def test_available_roles(self):
        """ Test available roles if we are reader and owner on a context
        providing IDossier of sharing
        """
        setRoles(self.portal, TEST_USER_ID, ['Reader', 'Role Manager'])
        expect = [
            u'Reader',
            u'Editor',
            u'Contributor',
            u'Reviewer',
            u'Publisher', ]
        self._check_roles(expect, self.view_dossier.available_roles())

    def test_manageable_roles_with_reader_and_owner(self):
        """ Test manageable roles if we are reader and owner on a context
        providing IDossier of sharing
        """
        setRoles(self.portal, TEST_USER_ID, ['Reader', 'Role Manager'])
        expect = [
            u'Reader',
            u'Editor',
            u'Contributor',
            u'Reviewer',
            u'Publisher',
            u'Administrator', ]
        self._check_roles(expect, self.view_dossier.roles())

    def test_info_tab_roles(self):
        """ Test the roles displayed in the info tab on a context
        providing IDossier of sharing
        """
        setRoles(self.portal, TEST_USER_ID, ['Reader', 'Role Manager'])
        expect = [
            u'Reader',
            u'Editor',
            u'Contributor',
            u'Reviewer',
            u'Publisher',
            u'DossierManager',
        ]
        self._check_roles(expect, self.tab_dossier.available_roles())

    def test_update_inherit(self):
        """ tests update inherit method

        We are owner of the portal, with inheritance we are also owner of
        the repo and dossier. If we disable role aquisition on context,
        we lose the role 'owner' on the context
        """

        register_event_recorder(ILocalRolesAcquisitionBlocked)
        register_event_recorder(ILocalRolesAcquisitionActivated)

        # We disable locale role aquisition on dossier
        self.view_dossier.update_inherit(False, reindex=False)
        last_event = get_last_recorded_event()
        self.assertTrue(ILocalRolesAcquisitionBlocked.providedBy(last_event))
        self.assertEquals(last_event.object, self.dossier)

        # we disable it again,it shouldn't fire a event because nothing changed
        self.view_dossier.update_inherit(False, reindex=False)
        self.assertEquals(last_event, get_last_recorded_event())

        # # We enable locale role aquisition on dossier
        self.view_dossier.update_inherit(True, reindex=False)
        # and check the fired event
        last_event = get_last_recorded_event()
        self.assertTrue(ILocalRolesAcquisitionActivated.providedBy(last_event))
        self.assertEquals(last_event.object, self.dossier)

        # we disable it again,it shouldn't fire a event because nothing changed
        self.view_dossier.update_inherit(True, reindex=False)
        self.assertEquals(last_event, get_last_recorded_event())

    def test_update_role_settings(self):
        """ Test update_role_settings method
        """
        register_event_recorder(ILocalRolesModified)

        # If nothing has changed it needs to be reported accordingly
        changed = self.view_repo.update_role_settings([], False)
        self.assertFalse(changed)

        # We try to add the new local role 'publisher'
        new_settings = \
            [{'type': 'user', 'id': 'test_user_1_', 'roles': ['Publisher']}, ]

        changed = self.view_repo.update_role_settings(new_settings, False)
        self.assertTrue(changed)

        last_event = get_last_recorded_event()
        # check the event type
        self.assertTrue(ILocalRolesModified.providedBy(last_event))
        # check the event context
        self.assertEquals(last_event.object, self.repo)
        # check the stored localroles
        self.assertEquals(last_event.old_local_roles,
                          {'test_user_1_': ('Owner',)})
        self.assertEquals(last_event.new_local_roles,
                          (('test_user_1_', ('Owner', 'Publisher')),))

        # now we remvove the local role 'publisher'
        new_settings = \
            [{'type': 'user', 'id': 'test_user_1_', 'roles': []}, ]

        changed = self.view_repo.update_role_settings(new_settings, False)
        self.assertTrue(changed)

        # check event attributes
        last_event = get_last_recorded_event()
        self.assertTrue(ILocalRolesModified.providedBy(last_event))
        self.assertEquals(last_event.object, self.repo)
        self.assertEquals(last_event.old_local_roles,
                          {'test_user_1_': ('Owner', 'Publisher')})
        self.assertTrue(
            last_event.new_local_roles == (('test_user_1_', ('Owner',)),))

    def test_sharing_view_only_returns_users_from_current_admin_unit(self):
        # create other group, from different admin unit

        other_admin_unit = create(Builder('admin_unit').id('other'))
        test_peter = create(Builder('ogds_user')
                            .id('test.peter')
                            .having(firstname='User',
                                    lastname='Test'))
        create(Builder('org_unit')
               .id(u'otherunit')
               .having(admin_unit=other_admin_unit)
               .assign_users([test_peter]))

        # create "current" admin unit
        test_user = create(Builder('ogds_user')
                           .having(firstname='User', lastname='Test'))

        admin_unit = create(Builder('admin_unit')
                            .as_current_admin_unit())

        create(Builder('org_unit')
               .id(u'testunit')
               .having(admin_unit=admin_unit)
               .as_current_org_unit()
               .assign_users([test_user]))

        self.portal.REQUEST.form['search_term'] = TEST_USER_NAME
        results = self.view_dossier.user_search_results()
        self.assertEqual(1, len(results))
        self.assertEqual(TEST_USER_ID, results[0]['id'])


class TestOpengeverSharingWithBrowser(IntegrationTestCase):

    @browsing
    def test_sharing_views(self, browser):
        """ Test Integration of opengever.sharing
        """
        self.login(self.manager, browser)

        browser.open(self.dossier)
        tabbedview.open('Info')

        expected_users_and_roles = [
            'Logged-in users',
            'fa_users',
            u'B\xe4rfuss K\xe4thi (kathi.barfuss)',
            u'Fr\xfchling F\xe4ivel (faivel.fruhling)',
            u'K\xf6nig J\xfcrgen (jurgen.konig)',
            ]

        found_users_and_roles = browser.css('#user-group-sharing-settings tr').text

        self.assertEqual(expected_users_and_roles, found_users_and_roles)

    @browsing
    def test_sharing_info_view_urlencodes_links_with_spaces(self, browser):
        self.login(self.regular_user, browser)

        group = create(Builder('group').with_groupid('with spaces'))
        api.group.grant_roles(
            group=group,
            obj=self.dossier,
            roles=['Publisher'])

        browser.open(self.dossier)
        tabbedview.open('Info')

        group_links = [a.get('href') for a
                       in browser.css('#user-group-sharing-settings tr a')]

        self.assertEqual(
            ['http://nohost/plone/@@list_groupmembers?group=fa_users',
             'http://nohost/plone/@@list_groupmembers?group=with+spaces'],
            group_links)

    @browsing
    def test_sharing_view_urlencodes_links_with_spaces(self, browser):
        self.login(self.manager, browser)

        group = create(Builder('group').with_groupid('with spaces'))
        api.group.grant_roles(
            group=group,
            obj=self.dossier,
            roles=['Publisher'])

        browser.open(self.dossier, view='@@sharing')

        group_links = [a.get('href') for a
                       in browser.css('#user-group-sharing-settings tr a')]

        self.assertEqual(
            ['http://nohost/plone/@@list_groupmembers?group=AuthenticatedUsers',
             'http://nohost/plone/@@list_groupmembers?group=fa_users',
             'http://nohost/plone/@@list_groupmembers?group=with+spaces'],
            group_links)

    @browsing
    def test_sharing_view_uses_group_title_attribute_if_exists(self, browser):
        self.login(self.manager, browser)

        inbox_group = get_current_org_unit().inbox_group
        inbox_group.title = u'The inbox group title'
        api.group.grant_roles(
            groupname=inbox_group.id(), obj=self.dossier, roles=['Publisher'])

        browser.open(self.dossier, view='@@sharing')
        self.assertEqual(
            ['Logged-in users',
             'The inbox group title (fa_inbox_users)',
             'fa_users'],
            browser.css('#user-group-sharing-settings tr a').text)
