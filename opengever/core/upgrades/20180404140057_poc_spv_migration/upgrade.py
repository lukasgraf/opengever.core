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

    def __init__(self, proposal_template):
        self.normalizer = getUtility(IIDNormalizer)
        self.proposal_template = proposal_template

    def get_data(self, proposal):
        root = {}
        root['mandant'] = {
            'name': get_current_admin_unit().title
        }

        # keep agenda items list for easier template reusability
        data = {}
        root['agenda_items'] = [data]

        data['title'] = proposal.title
        data['html:legal_basis'] = sanitize_text(proposal.legal_basis)
        data['html:initial_position'] = sanitize_text(proposal.initial_position)
        data['html:proposed_action'] = sanitize_text(proposal.proposed_action)
        data['html:decision_draft'] = sanitize_text(proposal.decision_draft)
        data['html:publish_in'] = sanitize_text(proposal.publish_in)
        data['html:disclose_to'] = sanitize_text(proposal.disclose_to)
        data['html:copy_for_attention'] = sanitize_text(proposal.copy_for_attention)
        return root

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
            url = '/'.join(proposal.absolute_url())
            msg = 'could not migrate propsal at: "{}"'.format(url)
            logger.error(msg)


class POCSPVMigration(UpgradeStep):
    """POC SPV migration.
    """

    def __call__(self):
        self.install_upgrade_profile()
        self.migrate_proposals()

    def migrate_proposals(self):
        proposal_template = UpgradeSablonTemplateWrapper(
            templates.load('template-proposal.docx'))
        migrator = ProposalMigrator(proposal_template)

        for proposal in self.objects(
                {'portal_type': 'opengever.meeting.proposal'},
                'Create proposal wordfiles'):
            migrator.migrate(proposal)
