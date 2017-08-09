from contextlib import nested
from ftw.testbrowser import browsing
from opengever.testing import IntegrationTestCase


class TestWordAgendaItem(IntegrationTestCase):
    features = ('meeting', 'word-meeting')

    def test_deciding_meeting_item_does_not_create_an_excerpt(self):
        """When the word meeting feature is enabled, deciding a meeting item
        does not create and return a excerpt document automatically;
        this must now be done by hand.
        """
        self.login(self.administrator)
        agenda_item = self.schedule_proposal(self.meeting,
                                             self.submitted_word_proposal)

        with nested(self.observe_children(self.dossier),
                    self.observe_children(self.meeting_dossier)) as \
                    (dossier_children,
                     meeting_dossier_children):
            agenda_item.decide()

        self.assertEquals((), tuple(dossier_children['added']))
        self.assertEquals((), tuple(meeting_dossier_children['added']))

    @browsing
    def test_proposal_document_in_meeting_item_data(self, browser):
        self.login(self.committee_responsible, browser)
        self.schedule_proposal(self.meeting,
                               self.submitted_word_proposal)
        browser.open(self.meeting, view='agenda_items/list')
        item_data = browser.json['items'][0]

        document_link_html = item_data.get('proposal_document_link')
        self.assertIn(
            u'Proposal document \xc4nderungen am Personalreglement',
            document_link_html)
        document = self.submitted_word_proposal.get_proposal_document()
        self.assertIn(document.absolute_url() + '/tooltip', document_link_html)

    @browsing
    def test_proposal_document_checkout_info_in_item_data(self, browser):
        self.login(self.committee_responsible, browser)
        agenda_item = self.schedule_proposal(self.meeting,
                                             self.submitted_word_proposal)
        browser.open(self.meeting, view='agenda_items/list')
        item_data = browser.json['items'][0]

        self.assertDictContainsSubset(
            {'proposal_document_checked_out': False,
             'edit_document_possible': True,
             'edit_document_link': self.agenda_item_url(agenda_item, 'edit_document')},
            item_data)

        document = self.submitted_word_proposal.get_proposal_document()
        self.checkout_document(document)
        browser.reload()
        item_data = browser.json['items'][0]
        self.assertDictContainsSubset(
            {'proposal_document_checked_out': True,
             'edit_document_possible': True},
            item_data)

    @browsing
    def test_edit_document_checks_out_and_provides_OC_url(self, browser):
        self.login(self.committee_responsible, browser)
        agenda_item = self.schedule_proposal(self.meeting,
                                             self.submitted_word_proposal)
        document = self.submitted_word_proposal.get_proposal_document()

        self.assertIsNone(self.get_checkout_manager(document).get_checked_out_by())
        browser.open(
            self.agenda_item_url(agenda_item, 'edit_document'),
            send_authenticator=True)

        self.assertEquals(
            {u'proceed': True,
             u'officeConnectorURL': u'{}/external_edit'.format(
                 document.absolute_url())},
            browser.json)
        self.assertEquals(self.committee_responsible.getId(),
                          self.get_checkout_manager(document).get_checked_out_by())

    @browsing
    def test_decide_agenda_item_checks_in_documents(self, browser):
        self.login(self.committee_responsible, browser)
        agenda_item = self.schedule_proposal(self.meeting,
                                             self.submitted_word_proposal)

        document = self.submitted_word_proposal.get_proposal_document()
        self.checkout_document(document)
        self.assertEqual(self.committee_responsible.getId(),
                         self.get_checkout_manager(document).get_checked_out_by())

        proposal_model = self.submitted_word_proposal.load_model()
        self.assertEquals(proposal_model.STATE_SCHEDULED, proposal_model.get_state())

        browser.open(
            self.agenda_item_url(agenda_item, 'decide'),
            send_authenticator=True)
        self.assertEquals(
            {u'redirectUrl': u'http://nohost/plone'
             '/opengever-meeting-committeecontainer/committee-1/meeting-1',
             u'messages': [
                 {u'messageTitle': u'Information',
                  u'message': u'Agenda Item decided and excerpt generated.',
                  u'messageClass': u'info'}]},
            browser.json)

        self.assertEquals(proposal_model.STATE_DECIDED, proposal_model.get_state())
        self.assertIsNone(self.get_checkout_manager(document).get_checked_out_by())

    @browsing
    def test_decide_agenda_item_disallowed_when_doc_checked_out(self, browser):
        """When an agenda items' proposal document is checkout by someone else,
        deciding the document is not allowed, since the system should not
        check in the documents checked out by other users.
        """

        self.login(self.committee_responsible, browser)
        agenda_item = self.schedule_proposal(self.meeting,
                                             self.submitted_word_proposal)

        self.login(self.administrator, browser)
        document = self.submitted_word_proposal.get_proposal_document()
        self.checkout_document(document)
        self.assertEqual(self.administrator.getId(),
                         self.get_checkout_manager(document).get_checked_out_by())

        self.login(self.committee_responsible, browser)
        proposal_model = self.submitted_word_proposal.load_model()
        self.assertEquals(proposal_model.STATE_SCHEDULED, proposal_model.get_state())

        browser.open(
            self.agenda_item_url(agenda_item, 'decide'),
            send_authenticator=True)
        self.assertEquals(
            {u'messages': [
                {u'messageTitle': u'Error',
                 u'message': u'Cannot decide agenda item: someone else has'
                 u' checked out the document.',
                 u'messageClass': u'error'}],
             u'proceed': False},
            browser.json)

        self.assertEquals(proposal_model.STATE_SCHEDULED, proposal_model.get_state())
        self.assertEqual(self.administrator.getId(),
                         self.get_checkout_manager(document).get_checked_out_by())

    @browsing
    def test_create_excerpt(self, browser):
        """When creating an excerpt of an agenda item, it should copy the
        proposal document into the meeting dossier for further editing.
        """
        self.login(self.committee_responsible, browser)
        agenda_item = self.schedule_proposal(self.meeting,
                                             self.submitted_word_proposal)
        agenda_item.decide()
        self.assertEquals(self.meeting.model.STATE_HELD,
                          self.meeting.model.get_state())

        browser.open(self.meeting, view='agenda_items/list')
        item_data = browser.json['items'][0]

        # The generate excerpt link is available on decided agenda items.
        self.assertDictContainsSubset(
            {'generate_excerpt_link': self.agenda_item_url(agenda_item, 'generate_excerpt')},
            item_data)

        # Create an excerpt.
        with self.observe_children(self.meeting_dossier) as children:
            browser.open(item_data['generate_excerpt_link'], send_authenticator=True)

        # Generating the excerpt is confirmed with a status message.
        self.assertEquals(
            {u'proceed': True,
             u'messages': [
                 {u'messageTitle': u'Information',
                  u'message': u'Excerpt was created successfully.',
                  u'messageClass': u'info'}]},
            browser.json)

        # The excerpt was created in the meeting dossier and contains the exact
        # original document.
        self.assertEquals(1, len(children['added']))
        excerpt_document ,= children['added']
        self.assertEquals('Excerpt \xc3\x84nderungen am Personalreglement',
                          excerpt_document.Title())
        self.assertEquals('file body', excerpt_document.file.data)

    @browsing
    def test_cannot_create_excerpt_when_meeting_closed(self, browser):
        self.login(self.committee_responsible, browser)
        agenda_item = self.schedule_proposal(self.meeting,
                                             self.submitted_word_proposal)
        agenda_item.decide()
        self.meeting.model.execute_transition('held-closed')
        self.assertEquals(self.meeting.model.STATE_CLOSED,
                          self.meeting.model.get_state())

        with browser.expect_unauthorized():
            browser.open(self.agenda_item_url(agenda_item, 'generate_excerpt'))

    @browsing
    def test_cannot_create_excerpt_when_item_not_decided(self, browser):
        self.login(self.committee_responsible, browser)
        agenda_item = self.schedule_proposal(self.meeting,
                                             self.submitted_word_proposal)
        with browser.expect_http_error(reason='Forbidden'):
            browser.open(self.agenda_item_url(agenda_item, 'generate_excerpt'))

    @browsing
    def test_error_when_no_access_to_meeting_dossier(self, browser):
        with self.login(self.administrator):
            self.committee_container.manage_setLocalRoles(
                self.regular_user.getId(), ('Reader',))
            self.committee.manage_setLocalRoles(
                self.regular_user.getId(), ('CommitteeGroupMember', 'Editor'))
            self.committee_container.reindexObjectSecurity()
            # Let regular_user have no access to meeting_dossier
            self.meeting_dossier.__ac_local_roles_block__ = True

        self.login(self.regular_user, browser)
        agenda_item = self.schedule_proposal(self.meeting,
                                             self.submitted_word_proposal)
        agenda_item.decide()

        browser.open(self.agenda_item_url(agenda_item, 'generate_excerpt'))
        self.assertEquals(
            {u'messages': [
                {u'messageTitle': u'Error',
                 u'message': u'Insufficient privileges to add a document'
                 u' to the meeting dossier.',
                 u'messageClass': u'error'}],
             u'proceed': False},
            browser.json)

    @browsing
    def test_excerpts_listed_in_meeting_item_data(self, browser):
        self.login(self.committee_responsible, browser)
        agenda_item = self.schedule_proposal(self.meeting,
                                             self.submitted_word_proposal)
        agenda_item.decide()

        browser.open(self.meeting, view='agenda_items/list')
        item_data = browser.json['items'][0]
        self.assertFalse(item_data.get('excerpts'))

        excerpt = self.submitted_word_proposal.generate_excerpt(
            self.meeting_dossier)

        browser.open(self.meeting, view='agenda_items/list')
        item_data = browser.json['items'][0]
        excerpt_links = item_data.get('excerpts', None)
        self.assertEquals(1, len(excerpt_links))
        self.assertIn('href="{}"'.format(excerpt.absolute_url()), excerpt_links[0])

    def agenda_item_url(self, agenda_item, endpoint):
        return '{}/agenda_items/{}/{}'.format(
            agenda_item.meeting.get_url(view=None),
            agenda_item.agenda_item_id,
            endpoint)
