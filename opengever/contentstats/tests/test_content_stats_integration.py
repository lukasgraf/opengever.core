from ftw.contentstats.interfaces import IStatsKeyFilter
from ftw.contentstats.interfaces import IStatsProvider
from ftw.testbrowser import browsing
from opengever.document.interfaces import ICheckinCheckoutManager
from opengever.testing import IntegrationTestCase
from plone import api
from zope.component import getMultiAdapter


class TestContentStatsIntegration(IntegrationTestCase):

    def test_portal_types_filter(self):
        self.login(self.regular_user)
        flt = getMultiAdapter(
            (self.portal, self.portal.REQUEST),
            IStatsKeyFilter, name='portal_types')

        # Obviously the core GEVER types should be kept
        self.assertTrue(flt.keep('opengever.document.document'))
        self.assertTrue(flt.keep('opengever.dossier.businesscasedossier'))
        self.assertTrue(flt.keep('opengever.task.task'))

        # As well as ftw.mail
        self.assertTrue(flt.keep('ftw.mail.mail'))

        # These uninteresting top level types should be ignored though
        self.assertFalse(flt.keep('opengever.dossier.templatefolder'))
        self.assertFalse(flt.keep('opengever.repository.repositoryroot'))
        self.assertFalse(flt.keep('opengever.inbox.inbox'))
        self.assertFalse(flt.keep('opengever.inbox.yearfolder'))
        self.assertFalse(flt.keep('opengever.inbox.container'))
        self.assertFalse(flt.keep('opengever.contact.contactfolder'))
        self.assertFalse(flt.keep('opengever.meeting.committeecontainer'))

        # Stock Plone types should be skipped as well
        self.assertFalse(flt.keep('ATBooleanCriterion'))
        self.assertFalse(flt.keep('ATCurrentAuthorCriterion'))
        self.assertFalse(flt.keep('ATDateCriteria'))
        self.assertFalse(flt.keep('ATDateRangeCriterion'))
        self.assertFalse(flt.keep('ATListCriterion'))
        self.assertFalse(flt.keep('ATPathCriterion'))
        self.assertFalse(flt.keep('ATRelativePathCriterion'))
        self.assertFalse(flt.keep('ATPortalTypeCriterion'))
        self.assertFalse(flt.keep('ATReferenceCriterion'))
        self.assertFalse(flt.keep('ATSelectionCriterion'))
        self.assertFalse(flt.keep('ATSimpleIntCriterion'))
        self.assertFalse(flt.keep('ATSimpleStringCriterion'))
        self.assertFalse(flt.keep('ATSortCriterion'))
        self.assertFalse(flt.keep('Discussion Item'))
        self.assertFalse(flt.keep('Document'))
        self.assertFalse(flt.keep('Event'))
        self.assertFalse(flt.keep('File'))
        self.assertFalse(flt.keep('Folder'))
        self.assertFalse(flt.keep('Image'))
        self.assertFalse(flt.keep('Link'))
        self.assertFalse(flt.keep('News Item'))
        self.assertFalse(flt.keep('Plone Site'))
        self.assertFalse(flt.keep('TempFolder'))
        self.assertFalse(flt.keep('Topic'))
        self.assertFalse(flt.keep('Collection'))

        # But any potential future type in opengever.* should be kept
        self.assertTrue(flt.keep('opengever.doesnt.exist.just.yet'))

    def test_review_states_filter(self):
        self.login(self.regular_user)
        flt = getMultiAdapter(
            (self.portal, self.portal.REQUEST),
            IStatsKeyFilter, name='review_states')

        states_to_keep = [
            'contact-state-active',
            'disposition-state-appraised',
            'disposition-state-archived',
            'disposition-state-closed',
            'disposition-state-disposed',
            'disposition-state-in-progress',
            'document-state-draft',
            'document-state-removed',
            'document-state-shadow',
            'dossier-state-active',
            'dossier-state-archived',
            'dossier-state-inactive',
            'dossier-state-offered',
            'dossier-state-resolved',
            'folder-state-active',
            'forwarding-state-closed',
            'forwarding-state-open',
            'forwarding-state-refused',
            'mail-state-active',
            'mail-state-removed',
            'opengever_committee_workflow--STATUS--active',
            'opengever_committee_workflow--STATUS--inactive',
            'proposal-state-active',
            'proposal-state-submitted',
            'repositoryfolder-state-active',
            'repositoryfolder-state-inactive',
            'task-state-cancelled',
            'task-state-in-progress',
            'task-state-open',
            'task-state-rejected',
            'task-state-resolved',
            'task-state-tested-and-closed',
            'tasktemplate-state-active',
            'tasktemplatefolder-state-activ',
            'tasktemplatefolder-state-inactiv',
        ]

        states_to_ignore = [
            # Stock Plone type states
            'external',
            'internal',
            'internally_published',
            'pending',
            'private',
            'published',
            'visible',

            # Uninteresting top level GEVER type states
            'contactfolder-state-active',
            'inbox-state-default',
            'opengever_committeecontainer_workflow--STATUS--active',
            'repositoryroot-state-active',
            'templatefolder-state-active',
        ]

        for state in states_to_keep:
            self.assertTrue(
                flt.keep(state),
                'Expected state %r to be kept by filter (was ignored)' % state)

        for state in states_to_ignore:
            self.assertFalse(
                flt.keep(state),
                'Expected state %r to be ignored by filter (was kept)' % state)

        # Collect a list of ALL the currently possible workflow states
        all_possible_workflow_states = set()
        wftool = api.portal.get_tool('portal_workflow')
        for workflow in wftool.objectValues():
            for wfstate in workflow.states.objectIds():
                all_possible_workflow_states.add(wfstate)

        covered_states = set(states_to_keep + states_to_ignore)
        non_existing_states = covered_states - all_possible_workflow_states

        self.assertEquals(
            set(), non_existing_states,
            'Found test for one or more non-existent '
            'workflow states:\n %r' % non_existing_states)

        self.assertEquals(
            all_possible_workflow_states, covered_states,
            'Missing test assertion for one or more states. Please add '
            'explicit assertions for the following workflow states:\n'
            '%r' % (all_possible_workflow_states - covered_states))

    def test_checked_out_docs_stats_provider(self):
        self.login(self.regular_user)
        stats_provider = getMultiAdapter(
            (self.portal, self.portal.REQUEST),
            IStatsProvider, name='checked_out_docs')

        self.assertEqual({'checked_out': 0, 'checked_in': 18},
                         stats_provider.get_raw_stats())

        # Check out a document
        getMultiAdapter((self.document, self.document.REQUEST),
                        ICheckinCheckoutManager).checkout()

        self.assertEqual({'checked_out': 1, 'checked_in': 17},
                         stats_provider.get_raw_stats())

    def test_file_mimetypes_provider(self):
        self.login(self.regular_user)
        stats_provider = getMultiAdapter(
            (self.portal, self.portal.REQUEST),
            IStatsProvider, name='file_mimetypes')

        raw_mimetype_stats = stats_provider.get_raw_stats()

        # Shadow documents and documents without files
        self.assertIn(
            '',
            raw_mimetype_stats,
        )
        self.assertEquals(2, raw_mimetype_stats.get('', None))

        self.assertIn(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            raw_mimetype_stats,
        )
        self.assertEquals(1, raw_mimetype_stats.get('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', None))

        self.assertIn(
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            raw_mimetype_stats,
        )
        self.assertEquals(11, raw_mimetype_stats.get('application/vnd.openxmlformats-officedocument.wordprocessingml.document', None))

        self.assertIn(
            'message/rfc822',
            raw_mimetype_stats,
        )
        self.assertEquals(2, raw_mimetype_stats.get('message/rfc822', None))

    @browsing
    def test_file_mimetypes_provider_in_view(self, browser):
        self.login(self.manager, browser)

        browser.open(self.portal, view='@@content-stats')
        table = browser.css('#content-stats-file_mimetypes').first

        # Shadow documents and documents without files
        self.assertIn(
            ['', '', '2'],
            table.lists(),
            )

        self.assertIn(
            ['', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '1'],
            table.lists(),
            )

        self.assertIn(
            ['', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', '11'],
            table.lists(),
            )

        self.assertIn(
            ['', 'message/rfc822', '2'],
            table.lists(),
            )

    @browsing
    def test_checked_out_docs_stats_provider_in_view(self, browser):
        self.login(self.manager, browser)

        browser.open(self.portal, view='@@content-stats')
        table = browser.css('#content-stats-checked_out_docs').first

        self.assertEquals(
            [['', 'checked_in', '18'], ['', 'checked_out', '0']],
            table.lists())

        # Check out a document
        getMultiAdapter((self.document, self.document.REQUEST),
                        ICheckinCheckoutManager).checkout()

        browser.open(self.portal, view='@@content-stats')
        table = browser.css('#content-stats-checked_out_docs').first

        self.assertEquals(
            [['', 'checked_in', '17'], ['', 'checked_out', '1']],
            table.lists())
