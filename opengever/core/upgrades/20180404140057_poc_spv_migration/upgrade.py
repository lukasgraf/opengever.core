from . import templates
from ftw.upgrade import UpgradeStep
from opengever.meeting.sablon import Sablon
from opengever.ogds.base.utils import get_current_admin_unit
from os.path import join
from plone.i18n.normalizer.interfaces import IIDNormalizer
from zope.component import getUtility
import json
import logging


logger = logging.getLogger('opengever.core')
MIME_DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


def sanitize_text(text):
    """Copied from AgendaItem. IIRC sablon is a bit sensitive and does not
    treat empty strings falsy.
    """
    if not text:
        return None
    return text


class UpgradeSablonTemplateWrapper(object):

    def __init__(self, data):
        self.data = data

    def as_file(self, path):
        file_path = join(path, 'template.docx')
        with open(file_path, 'wb') as template_file:
            template_file.write(self.data)
        return file_path


class ProposalMigrator(object):
    """Generate Word *.docx files for porposals in a dossier based on their
    fields and a sablon template.
    """
    def __init__(self, proposal_template):
        self.normalizer = getUtility(IIDNormalizer)
        self.proposal_template = proposal_template

    def get_data(self, proposal):
        root = {}
        root['mandant'] = {
            'name': get_current_admin_unit().title
        }

        # keep agenda items list for easier template reusability
        root['agenda_items'] = [self.get_agenda_item_data(proposal)]
        return root

    def get_agenda_item_data(self, proposal):
        """Build data for one proposal.

        We call it agenda_item here as this is the name used in the templates.
        To make existing templates reusable for the miration we don't change
        the data structre.
        """
        data = {}

        data['title'] = proposal.title
        data['html:legal_basis'] = sanitize_text(proposal.legal_basis)
        data['html:initial_position'] = sanitize_text(proposal.initial_position)
        data['html:proposed_action'] = sanitize_text(proposal.proposed_action)
        data['html:decision_draft'] = sanitize_text(proposal.decision_draft)
        data['html:publish_in'] = sanitize_text(proposal.publish_in)
        data['html:disclose_to'] = sanitize_text(proposal.disclose_to)
        data['html:copy_for_attention'] = sanitize_text(proposal.copy_for_attention)
        return data

    def get_json_data(self, proposal):
        return json.dumps(self.get_data(proposal))

    def migrate(self, proposal):
        sablon = Sablon(self.proposal_template)
        sablon.process(self.get_json_data(proposal))
        if sablon.is_processed_successfully():
            filename = u"{}.docx".format(
                self.normalizer.normalize(proposal.title))
            proposal.create_proposal_document(
                filename=filename,
                data=sablon.file_data,
                content_type=MIME_DOCX)
        else:
            url = proposal.absolute_url()
            msg = 'Could not generate sablon document: "{}"'.format(url)
            logger.error(msg)
            logger.error(sablon.stderr)


class SubmittedProposalMigrator(ProposalMigrator):
    """Generate Word *.docx files for submitted porposals in a committee based
    on their fields and a sablon template.
    """
    def get_agenda_item_data(self, submitted_proposal):
        data = super(SubmittedProposalMigrator, self).get_agenda_item_data(
            submitted_proposal)

        data['html:considerations'] = sanitize_text(
            submitted_proposal.considerations)

        model = submitted_proposal.load_model()
        data['html:decision'] = sanitize_text(model.get_decision())

        agenda_item = model.agenda_item
        # huh, no getter there?
        discussion = agenda_item.discussion if agenda_item else None
        data['html:discussion'] = sanitize_text(discussion)

        data['decision_number'] = model.get_decision_number()
        data['dossier_reference_number'] = model.dossier_reference_number
        data['repository_folder_title'] = model.repository_folder_title

        return data


class POCSPVMigration(UpgradeStep):
    """POC SPV migration.
    """
    def __call__(self):
        self.install_upgrade_profile()
        self.migrate_proposals()
        self.migrate_submitted_proposals()

    def migrate_proposals(self):
        proposal_template = UpgradeSablonTemplateWrapper(
            templates.load('template-proposal.docx'))
        migrator = ProposalMigrator(proposal_template)

        for proposal in self.objects(
                {'portal_type': 'opengever.meeting.proposal'},
                'Create proposal documents'):
            migrator.migrate(proposal)

    def migrate_submitted_proposals(self):
        submitted_proposal_template = UpgradeSablonTemplateWrapper(
            templates.load('template-submittedproposal.docx'))
        migrator = SubmittedProposalMigrator(submitted_proposal_template)

        for submitted_proposal in self.objects(
                {'portal_type': 'opengever.meeting.submittedproposal'},
                'Create submitted proposal documents'):
            migrator.migrate(submitted_proposal)
