from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browsing
from ftw.testbrowser.pages import factoriesmenu
from ftw.testbrowser.pages import plone
from ftw.testbrowser.pages import statusmessages
from opengever.meeting.command import MIME_DOCX
from opengever.meeting.model import Proposal
from opengever.meeting.proposal import ISubmittedProposal
from opengever.officeconnector.helpers import is_officeconnector_checkout_feature_enabled  # noqa
from opengever.testing import IntegrationTestCase
from plone import api
from zc.relation.interfaces import ICatalog
from zope.component import getUtility


VIEW_PERMISSIONS = (
    'Access contents information',
    'CMFEditions: Access previous versions',
    'View',
)


class TestProposalWithWord(IntegrationTestCase):
    features = ('meeting',)

    @browsing
    def test_creating_proposal_from_proposal_template(self, browser):
        self.login(self.dossier_responsible, browser)
        browser.open(self.dossier)
        factoriesmenu.add('Proposal')
        browser.fill(
            {'Title': u'Baugesuch Kreuzachkreisel',
             'Committee': u'Rechnungspr\xfcfungskommission',
             'Proposal template': u'Geb\xfchren',
             'Edit after creation': True}).save()
        statusmessages.assert_no_error_messages()
        self.assertIn('external_edit', browser.css('.redirector').first.text,
                      'External editor should have been triggered.')

        proposal = browser.context
        browser.open(proposal, view='tabbedview_view-overview')
        self.assertEquals(
            [['Title', u'Baugesuch Kreuzachkreisel'],
             ['Committee', u'Rechnungspr\xfcfungskommission'],
             ['Meeting', ''],
             ['Proposal document',
              'Baugesuch Kreuzachkreisel'],
             ['State', 'Pending'],
             ['Decision number', '']],
            browser.css('table.listing').first.lists())

        browser.click_on('Baugesuch Kreuzachkreisel')
        browser.open(browser.context, view='tabbedview_view-overview')
        self.assertDictContainsSubset(
            {'Title': u'Baugesuch Kreuzachkreisel'},
            dict(browser.css('table.listing').first.lists()))

        self.assertEquals(
            self.proposal_template.file.data,
            proposal.get_proposal_document().file.data)

        self.assertFalse(
            is_officeconnector_checkout_feature_enabled(),
            'Office connector checkout feature is now active: this means'
            ' that the document will no longer be checked out in the proposal'
            ' creation wizard and therefore the assertion "document is checked'
            ' out" will therefore fail.')
        self.assertEquals(
            self.dossier_responsible.getId(),
            self.get_checkout_manager(
                proposal.get_proposal_document()).get_checked_out_by())

    @browsing
    def test_proposal_document_is_visible_on_submitted_proposal(self, browser):
        self.login(self.committee_responsible, browser)
        browser.open(self.submitted_word_proposal, view='tabbedview_view-overview')
        self.assertEquals(
            [['Title', u'\xc4nderungen am Personalreglement'],
             ['Committee', u'Rechnungspr\xfcfungskommission'],
             ['Dossier', u'Vertr\xe4ge mit der kantonalen Finanzverwaltung'],
             ['Meeting', ''],
             ['Proposal document',
              u'\xc4nderungen am Personalreglement'],
             ['State', 'Submitted'],
             ['Decision number', ''],
             ['Attachments', u'Vertr\xe4gsentwurf']],
            browser.css('table.listing').first.lists())

    @browsing
    def test_visible_fields_in_addform(self, browser):
        """When the "word implementation" feature is enabled,
        the "old" trix fields should disappear.
        """
        self.login(self.dossier_responsible, browser)
        browser.open(self.dossier)
        factoriesmenu.add('Proposal')
        hidden = ('Legal basis',
                  'Initial position',
                  'Proposed action',
                  'Decision draft',
                  'Publish in',
                  'Disclose to',
                  'Copy for attention')
        missing = tuple(set(hidden) - set(browser.forms['form'].field_labels))
        self.assertItemsEqual(hidden, missing)

    @browsing
    def test_word_proposal_can_be_submitted(self, browser):
        self.login(self.dossier_responsible, browser)
        self.assertEqual(Proposal.STATE_PENDING,
                         self.draft_word_proposal.get_state())
        self.assertEqual('proposal-state-active',
                         api.content.get_state(self.draft_word_proposal))

        browser.open(self.draft_word_proposal, view='tabbedview_view-overview')
        browser.click_on('Submit')
        statusmessages.assert_no_error_messages()
        statusmessages.assert_message('Proposal successfully submitted.')
        self.assertEqual(Proposal.STATE_SUBMITTED,
                         self.draft_word_proposal.get_state())
        self.assertEqual('proposal-state-submitted',
                         api.content.get_state(self.draft_word_proposal))

        self.login(self.administrator)
        model = self.draft_word_proposal.load_model()
        submitted_proposal = model.resolve_submitted_proposal()
        proposal_file = self.draft_word_proposal.get_proposal_document().file
        submitted_proposal_file = submitted_proposal.get_proposal_document().file
        with proposal_file.open() as expected:
            with submitted_proposal_file.open() as got:
                self.assertEquals(expected.read(), got.read())

    @browsing
    def test_document_of_draft_proposal_can_be_edited(self, browser):
        self.login(self.dossier_responsible, browser)
        document = self.draft_word_proposal.get_proposal_document()
        browser.open(document, view='edit')
        self.assertEquals('Edit Document', plone.first_heading(),
                          'Document should be editable.')

    @browsing
    def test_document_of_proposal_cannot_be_edited_when_submitted(self, browser):
        self.login(self.dossier_responsible, browser)
        document = self.word_proposal.get_proposal_document()
        with browser.expect_unauthorized():
            browser.open(document, view='edit')

    @browsing
    def test_document_of_rejected_proposal_can_be_edited(self, browser):
        self.login(self.committee_responsible, browser)
        browser.open(self.submitted_word_proposal, view='tabbedview_view-overview')
        browser.find('Reject').click()
        browser.fill({'Comment': u'Bitte \xfcberarbeiten'}).submit()

        self.login(self.dossier_responsible, browser)
        document = self.word_proposal.get_proposal_document()
        browser.open(self.word_proposal.get_proposal_document(), view='edit')
        browser.open(document, view='edit')
        self.assertEquals('Edit Document', plone.first_heading(),
                          'Document should be editable.')

    @browsing
    def test_prevent_trashing_proposal_document(self, browser):
        self.login(self.dossier_responsible, browser)
        self.assertFalse(
            api.user.has_permission(
                'opengever.trash: Trash content',
                obj=self.word_proposal.get_proposal_document()),
            'The proposal document should not be trashable.')
        self.assertFalse(
            api.user.has_permission(
                'opengever.trash: Trash content',
                obj=self.draft_word_proposal.get_proposal_document()),
            'The proposal document should not be trashable.')

    @browsing
    def test_proposal_cannot_change_state_when_documents_checked_out(self, browser):
        self.login(self.dossier_responsible, browser)
        document = self.draft_word_proposal.get_proposal_document()
        self.checkout_document(document)
        self.assertTrue(self.draft_word_proposal.contains_checked_out_documents())
        browser.open(self.draft_word_proposal, view='tabbedview_view-overview')
        browser.click_on('Submit')
        statusmessages.assert_message(
            'Cannot change the state because the proposal'
            ' contains checked out documents.')

    def test_decide_not_allowed_when_documents_checked_out(self):
        """When deciding the proposal on the proposal model, the proposal
        document must already be checked in.
        This also applies to the current user: the auto-checkin-feature is
        the job of the agenda item controller, not of the proposal model.
        """
        self.login(self.committee_responsible)
        item = self.schedule_proposal(self.meeting,
                                      self.submitted_word_proposal)
        self.checkout_document(self.submitted_word_proposal.get_proposal_document())

        model = self.submitted_word_proposal.load_model()
        with self.assertRaises(ValueError) as cm:
            model.decide(item)

        self.assertEquals(
            'Cannot decide proposal when proposal document is checked out.',
            str(cm.exception))

    def test_generate_excerpt_copies_document_to_target(self):
        self.login(self.administrator)
        self.assertEquals(
            [],
            ISubmittedProposal(self.submitted_word_proposal).excerpts)

        agenda_item = self.schedule_proposal(self.meeting,
                              self.submitted_word_proposal)
        agenda_item.decide()

        with self.observe_children(self.meeting_dossier) as children:
            agenda_item.generate_excerpt(title='Excerpt \xc3\x84nderungen')

        self.assertEquals(1, len(children['added']),
                          'An excerpt document should have been added to the'
                          ' meeting dossier.')

        # The document should contain a copy of the proposal document file.
        excerpt_document, = children['added']
        self.assertEquals('Excerpt \xc3\x84nderungen',
                          excerpt_document.Title())
        self.assertEquals(u'excerpt-anderungen.docx',
                          excerpt_document.file.filename)
        self.assertEquals(MIME_DOCX, excerpt_document.file.contentType)
        self.assertIsNotNone(excerpt_document.file.data)

        # The excerpt document should be referenced as relation.
        excerpts = ISubmittedProposal(self.submitted_word_proposal).excerpts
        self.assertEquals(1, len(excerpts))
        relation, = excerpts
        self.assertEquals(excerpt_document, relation.to_object)

        # The relation catalog should have catalogued the new relation.
        self.assertIn(relation,
                      tuple(getUtility(ICatalog).findRelations(
                          {'to_id': relation.to_id})))

    @browsing
    def test_create_successor_proposal(self, browser):
        self.login(self.dossier_responsible, browser)
        browser.open(self.word_proposal, view='tabbedview_view-overview')
        button_label = 'Create successor proposal'

        self.assertEquals('submitted', self.word_proposal.get_state().title)
        self.assertFalse(browser.find(button_label))

        with self.login(self.committee_responsible):
            agenda_item = self.schedule_proposal(self.meeting, self.submitted_word_proposal)
            self.assertEquals('scheduled', self.submitted_word_proposal.get_state().title)

        self.assertEquals('scheduled', self.word_proposal.get_state().title)
        self.assertFalse(browser.reload().find(button_label))

        with self.login(self.committee_responsible):
            agenda_item.decide()
            self.assertEquals('decided', self.submitted_word_proposal.get_state().title)

        self.assertEquals('decided', self.word_proposal.get_state().title)
        self.assertTrue(browser.reload().find(button_label))

        browser.click_on(button_label)

        self.assertEquals(
            self.word_proposal.Title().decode('utf-8'),
            browser.find('Title').value)
        self.assertEquals(
            str(self.word_proposal.get_committee().load_model().committee_id),
            browser.find('Committee').value)
        self.assertEquals(
            [rel.to_path for rel in self.word_proposal.relatedItems],
            [node.value for node
             in browser.find('Attachments').css('input[type=checkbox]')])

        self.assertIn(
            self.word_proposal.get_proposal_document().UID(),
            browser.find('Proposal template').options,
            'The proposal document of the predecessor should be selectable'
            ' as proposal template.')

        browser.fill({
            'Title': u'\xc4nderungen am Personalreglement zur Nachpr\xfcfung',
            'Proposal template': self.word_proposal.get_proposal_document().Title(),
        }).save()
        statusmessages.assert_no_error_messages()

        proposal = browser.context
        browser.open(proposal, view='tabbedview_view-overview')
        self.assertEquals(
            [['Title', u'\xc4nderungen am Personalreglement zur Nachpr\xfcfung'],
             ['Committee', u'Rechnungspr\xfcfungskommission'],
             ['Meeting', ''],
             ['Proposal document',
              u'\xc4nderungen am Personalreglement zur Nachpr\xfcfung'],
             ['State', 'Pending'],
             ['Decision number', ''],
             ['Predecessor', u'\xc4nderungen am Personalreglement'],
             ['Attachments', u'Vertr\xe4gsentwurf']],
            browser.css('table.listing').first.lists())

        browser.open(self.word_proposal, view='tabbedview_view-overview')
        self.assertIn(u'Successor proposal '
                      u'\xc4nderungen am Personalreglement zur Nachpr\xfcfung '
                      u'created by Ziegler Robert (robert.ziegler)',
                      browser.css('.answers .answerBody h3').text)
        self.assertEquals(
            [['Title', u'\xc4nderungen am Personalreglement'],
             ['Committee', u'Rechnungspr\xfcfungskommission'],
             ['Meeting', u'9. Sitzung der Rechnungspr\xfcfungskommission'],
             ['Proposal document', u'\xc4nderungen am Personalreglement'],
             ['State', 'Decided'],
             ['Decision number', '2016 / 2'],
             ['Successors', u'\xc4nderungen am Personalreglement zur Nachpr\xfcfung'],
             ['Attachments', u'Vertr\xe4gsentwurf']],
            browser.css('table.listing').first.lists())

    @browsing
    def test_committee_member_can_view_proposal_document(self, browser):
        """The meeting_user is a CommitteeMember, who can access the proposal and
        its document read-only.
        """
        self.login(self.meeting_user, browser)
        browser.open(self.submitted_word_proposal, view='tabbedview_view-overview')
        self.assertTrue(browser.find(u'\xc4nderungen am Personalreglement'))

        browser.open(self.submitted_word_proposal.get_proposal_document(),
                     view='tabbedview_view-overview')
        self.assertDictContainsSubset(
            {'Title': u'\xc4nderungen am Personalreglement'},
            dict(browser.css('.documentMetadata table').first.lists()))

    def test_committee_member_permissions_on_proposal_document(self):
        self.login(self.meeting_user)
        self.assert_has_permissions(
            VIEW_PERMISSIONS,
            self.submitted_word_proposal.get_proposal_document())

        self.assert_has_not_permissions(
            (
                'Modify portal content',
                'opengever.document: Checkout',
            ),
            self.submitted_word_proposal.get_proposal_document())

    def test_committee_responsible_can_edit_proposal_document(self):
        self.login(self.committee_responsible)
        self.assert_has_permissions(
            (
                'Access contents information',
                'CMFEditions: Access previous versions',
                'CMFEditions: Apply version control',
                'CMFEditions: Checkout to location',
                'CMFEditions: Manage versioning policies',
                'CMFEditions: Purge version',
                'CMFEditions: Revert to previous versions',
                'Change portal events',
                'Modify portal content',
                'View',
                'WebDAV Lock items',
                'WebDAV Unlock items',
                'WebDAV access',
                'opengever.document: Cancel',
                'opengever.document: Checkin',
                'opengever.document: Checkout',
            ),
            self.submitted_word_proposal.get_proposal_document())

    def test_committee_administrator_can_edit_proposal_document(self):
        self.login(self.administrator)
        self.assert_has_permissions(
            (
                'Access contents information',
                'CMFEditions: Access previous versions',
                'CMFEditions: Apply version control',
                'CMFEditions: Checkout to location',
                'CMFEditions: Manage versioning policies',
                'CMFEditions: Purge version',
                'CMFEditions: Revert to previous versions',
                'Change portal events',
                'Modify portal content',
                'View',
                'WebDAV Lock items',
                'WebDAV Unlock items',
                'WebDAV access',
                'opengever.document: Cancel',
                'opengever.document: Checkin',
                'opengever.document: Checkout',
            ),
            self.submitted_word_proposal.get_proposal_document())

    def test_access_to_mail_attached_to_proposal(self):
        with self.login(self.administrator):
            mail = create(Builder('mail').within(self.submitted_word_proposal))
            self.assert_has_permissions(VIEW_PERMISSIONS, mail,
                                        '(CommitteeAdministrator)')

        with self.login(self.committee_responsible):
            self.assert_has_permissions(VIEW_PERMISSIONS, mail,
                                        '(CommitteeResponsible)')

        with self.login(self.meeting_user):
            self.assert_has_permissions(VIEW_PERMISSIONS, mail,
                                        '(CommitteeMember)')

    @browsing
    def test_committee_member_should_not_be_able_to_reject_a_proposal(self, browser):
        """Regression test: committee members did see the "Reject" button,
        although it did not work.
        """
        self.login(self.meeting_user, browser)
        browser.open(self.submitted_word_proposal, view='tabbedview_view-overview')
        self.assertFalse(browser.find('Reject'))
