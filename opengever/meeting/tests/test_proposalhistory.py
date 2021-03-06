from ftw.testbrowser import browser as default_browser
from ftw.testbrowser import browsing
from opengever.meeting.interfaces import IHistory
from opengever.testing import IntegrationTestCase
from plone import api
from plone.namedfile.file import NamedBlobFile
from plone.protect import createToken


class TestIntegrationProposalHistory(IntegrationTestCase):

    features = (
        'meeting',
        )

    def open_overview(self, browser, proposal=None):
        proposal = proposal or self.proposal
        browser.open(proposal, view='tabbedview_view-overview')

    def get_latest_history_entry_text(self, browser):
        return browser.css('div.answers .answer h3').first.text

    def get_history_entries_text(self, browser):
        return browser.css('div.answers .answer h3').text

    def assert_proposal_history_records(
            self,
            expected_records,
            proposal=None,
            browser=default_browser,
            with_submitted=False
        ):
        """Assert that the last history entries of a proposal are correct.

        The parameter expected_records can be a string to assert for only the
        last history record or a list of entries to assert that the last n
        entries are correct.

        If with_submitted is True also assert that the history entries are
        present for the submitted proposal. In that case also assert that uuids
        of history entries from proposal and submitted proposal match.
        """
        if not proposal:
            proposal = self.proposal

        # assert proposal record(s)
        self.open_overview(browser, proposal)
        if isinstance(expected_records, basestring):
            self.assertEqual(expected_records, self.get_latest_history_entry_text(browser))
        else:
            nof_records = len(expected_records)
            self.assertSequenceEqual(expected_records, self.get_history_entries_text(browser)[:nof_records])

        if not with_submitted:
            return

        # assert submitted proposal record(s)
        proposal_model = proposal.load_model()
        submitted_proposal = proposal_model.resolve_submitted_proposal()
        self.open_overview(browser, submitted_proposal)
        if isinstance(expected_records, basestring):
            self.assertEqual(expected_records, self.get_latest_history_entry_text(browser))
        else:
            nof_records = len(expected_records)
            self.assertSequenceEqual(expected_records, self.get_history_entries_text(browser)[:nof_records])

        # assert uuid of proposal and submitted proposal record match
        proposal_history = IHistory(proposal)
        s_proposal_history = IHistory(submitted_proposal)
        proposal_history_record = list(proposal_history)[0]
        s_proposal_history_record = list(s_proposal_history)[0]
        self.assertEqual(proposal_history_record.uuid, s_proposal_history_record.uuid)

    @browsing
    def test_creation_creates_history_entry(self, browser):
        self.login(self.regular_user, browser)
        self.assert_proposal_history_records(
            u'Created by Ziegler Robert (robert.ziegler)',
            self.draft_proposal,
            browser,
            )

    @browsing
    def test_submitting_proposal_creates_history_entries(self, browser):
        self.login(self.regular_user, browser)
        self.open_overview(browser, self.draft_proposal)
        # submit proposal
        browser.css('#pending-submitted').first.click()
        expected_history = [u'Submitted by B\xe4rfuss K\xe4thi (kathi.barfuss)']
        with self.login(self.meeting_user, browser):
            self.assert_proposal_history_records(expected_history, self.draft_proposal, browser, with_submitted=True)

    @browsing
    def test_rejecting_proposals_creates_history_entries(self, browser):
        self.login(self.regular_user, browser)
        self.open_overview(browser, self.proposal)
        # reject submitted proposal
        submitted_proposal = self.proposal.load_model().resolve_submitted_proposal()
        with self.login(self.committee_responsible, browser):
            self.open_overview(browser, submitted_proposal)
            browser.find('Reject').click()
            browser.fill({'Comment': u'Bitte \xfcberarbeiten'}).submit()
        self.assert_proposal_history_records(u'Rejected by M\xfcller Fr\xe4nzi (franzi.muller)', self.proposal, browser)

    @browsing
    def test_cancelling_and_reactivating_proposal_creates_history_entry(self, browser):
        self.login(self.regular_user, browser)
        self.open_overview(browser, self.draft_proposal)
        # cancel proposal
        browser.css('#pending-cancelled').first.click()
        self.assert_proposal_history_records(
            u'Proposal cancelled by B\xe4rfuss K\xe4thi (kathi.barfuss)',
            self.draft_proposal,
            browser,
            )
        # reactivate proposal
        browser.css('#cancelled-pending').first.click()
        self.assert_proposal_history_records(
            u'Proposal reactivated by B\xe4rfuss K\xe4thi (kathi.barfuss)',
            self.draft_proposal,
            browser,
            )

    @browsing
    def test_submitting_additional_document_creates_history_entry(self, browser):
        self.login(self.regular_user, browser)
        browser.open(self.proposal)
        # submit additional document
        browser.find('Submit additional documents').click()
        browser.fill({'Attachments': self.subdocument})
        browser.find('Submit Attachments').click()
        with self.login(self.meeting_user, browser):
            self.assert_proposal_history_records(
                u'Document \xdcbersicht der Vertr\xe4ge von 2016 submitted in version 0 '
                u'by B\xe4rfuss K\xe4thi (kathi.barfuss)',
                self.proposal,
                browser,
                with_submitted=True,
                )

    @browsing
    def test_updating_existing_document_creates_history_entry(self, browser):
        self.login(self.regular_user, browser)
        self.document.file = NamedBlobFile('New', filename=u'test.txt')
        repository = api.portal.get_tool('portal_repository')
        repository.save(self.document)
        browser.open(self.proposal)
        browser.find('Submit additional documents').click()
        browser.fill({'Attachments': self.document})
        browser.find('Submit Attachments').click()
        with self.login(self.meeting_user, browser):
            self.assert_proposal_history_records(
                u'Submitted document Vertr\xe4gsentwurf updated to version 1 by B\xe4rfuss K\xe4thi (kathi.barfuss)',
                self.proposal,
                browser,
                with_submitted=True,
                )

    @browsing
    def test_scheduling_creates_history_entry(self, browser):
        self.login(self.meeting_user, browser)
        scheduling_url = self.meeting.model.get_url(view='unscheduled_proposals/1/schedule')
        with self.login(self.committee_responsible, browser):
            browser.open(scheduling_url)
        self.assert_proposal_history_records(
            u'Scheduled for meeting 9. Sitzung der Rechnungspr\xfcfungskommission '
            u'by M\xfcller Fr\xe4nzi (franzi.muller)',
            self.proposal,
            browser,
            with_submitted=True,
            )

    @browsing
    def test_removing_from_schedule_creates_history_entry(self, browser):
        self.login(self.meeting_user, browser)
        scheduling_url = self.meeting.model.get_url(view='unscheduled_proposals/1/schedule')
        unscheduling_url = self.meeting.model.get_url(view='agenda_items/2/delete')
        with self.login(self.committee_responsible, browser):
            browser.open(scheduling_url)
            browser.open(unscheduling_url)
        self.assert_proposal_history_records(
            u'Removed from schedule of meeting 9. Sitzung der Rechnungspr\xfcfungskommission '
            u'by M\xfcller Fr\xe4nzi (franzi.muller)',
            self.proposal,
            browser,
            with_submitted=True,
            )

    @browsing
    def test_reopening_creates_history_entry(self, browser):
        self.login(self.meeting_user, browser)
        scheduling_url = self.meeting.model.get_url(view='unscheduled_proposals/1/schedule')
        deciding_url = self.meeting.model.get_url(view='agenda_items/2/decide')
        reopening_url = self.meeting.model.get_url(view='agenda_items/2/reopen')
        with self.login(self.committee_responsible, browser):
            browser.open(scheduling_url)
            browser.open(deciding_url, data={'_authenticator': createToken()})
            browser.open(reopening_url, data={'_authenticator': createToken()})
        self.assert_proposal_history_records(
            u'Proposal reopened by M\xfcller Fr\xe4nzi (franzi.muller)',
            self.proposal,
            browser,
            with_submitted=True,
            )

    @browsing
    def test_deciding_creates_history_entry(self, browser):
        self.login(self.meeting_user, browser)
        scheduling_url = self.meeting.model.get_url(view='unscheduled_proposals/1/schedule')
        deciding_url = self.meeting.model.get_url(view='agenda_items/2/decide')
        with self.login(self.committee_responsible, browser):
            browser.open(scheduling_url)
            browser.open(deciding_url, data={'_authenticator': createToken()})
        self.assert_proposal_history_records(
            u'Proposal decided by M\xfcller Fr\xe4nzi (franzi.muller)',
            self.proposal,
            browser,
            with_submitted=True,
            )

    @browsing
    def test_revising_creates_history_entry(self, browser):
        self.login(self.meeting_user, browser)
        scheduling_url = self.meeting.model.get_url(view='unscheduled_proposals/1/schedule')
        deciding_url = self.meeting.model.get_url(view='agenda_items/2/decide')
        reopening_url = self.meeting.model.get_url(view='agenda_items/2/reopen')
        revising_url = self.meeting.model.get_url(view='agenda_items/2/revise')
        with self.login(self.committee_responsible, browser):
            browser.open(scheduling_url)
            browser.open(deciding_url, data={'_authenticator': createToken()})
            browser.open(reopening_url, data={'_authenticator': createToken()})
            browser.open(revising_url, data={'_authenticator': createToken()})
        self.assert_proposal_history_records(
            u'Proposal revised by M\xfcller Fr\xe4nzi (franzi.muller)',
            self.proposal,
            browser,
            with_submitted=True,
            )
