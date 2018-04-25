from . import templates
from opengever.base.command import CreateDocumentCommand
from opengever.base.oguid import Oguid
from opengever.core.upgrade import SQLUpgradeStep
from opengever.meeting.model import AgendaItem
from opengever.meeting.sablon import Sablon
from opengever.ogds.base.utils import get_current_admin_unit
from os.path import join
from persistent.dict import PersistentDict
from plone import api
from plone.i18n.normalizer.interfaces import IIDNormalizer
from sqlalchemy.sql import select
from sqlalchemy.sql.expression import column
from sqlalchemy.sql.expression import table
from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility
import itertools
import json
import logging


logger = logging.getLogger('opengever.core')
MIME_DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
LEGACY_DATA_KEY = 'legacy_meeting_proposal_fields'


meeting_excerpts = table(
    'meeting_excerpts',
    column('meeting_id'),
    column('document_id'),
)

generateddocuments_table = table(
    'generateddocuments',
    column('id'),
)


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
    fields = (
        'legal_basis',
        'initial_position',
        'proposed_action',
        'decision_draft',
        'publish_in',
        'disclose_to',
        'copy_for_attention',
    )

    def __init__(self, proposal_template):
        self.normalizer = getUtility(IIDNormalizer)
        self.proposal_template = proposal_template

    def migrate(self, proposal):
        self.generate_word_file(proposal)
        self.move_fields_to_annotations(proposal)

    def generate_word_file(self, proposal):
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

    def move_fields_to_annotations(self, proposal):
        """Remember old html field values in proposal's annotations."""

        annotations = IAnnotations(proposal)
        if LEGACY_DATA_KEY not in annotations:
            annotations[LEGACY_DATA_KEY] = PersistentDict()
        field_backup = annotations[LEGACY_DATA_KEY]

        for name in self.fields:
            field_backup[name] = getattr(proposal, name)

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

        for name in self.fields:
            value = getattr(proposal, name)
            data_key = 'html:{}'.format(name)
            data[data_key] = sanitize_text(value)
        return data

    def get_json_data(self, proposal):
        return json.dumps(self.get_data(proposal))


class SubmittedProposalMigrator(ProposalMigrator):
    """Generate Word *.docx files for submitted porposals in a committee based
    on their fields and a sablon template.
    """

    fields = ProposalMigrator.fields + (
        'considerations',
    )
    def migrate(self, submitted_proposal):
        super(SubmittedProposalMigrator, self).migrate(submitted_proposal)
        self.migrate_excerpts(submitted_proposal)

    def move_fields_to_annotations(self, submitted_proposal):
        super(SubmittedProposalMigrator, self).move_fields_to_annotations(submitted_proposal)

        model = submitted_proposal.load_model()
        agenda_item = model.agenda_item
        if not agenda_item:
            return

        field_backup = IAnnotations(submitted_proposal)[LEGACY_DATA_KEY]
        field_backup['decision'] = agenda_item.decision
        field_backup['discussion'] = agenda_item.discussion

    def migrate_excerpts(self, submitted_proposal):
        """Excerpts are now also tracked in a relation list. Before migrating
        we would only allow one excerpt per proposal. Now there can be
        multiple. So all we have to do is append the one excerpt to the list
        of ecxerpts.

        Also the excerpt documents are now stored in the meeting dossier, and
        no longer inside the proposal.
        """
        proposal_model = submitted_proposal.load_model()
        if not proposal_model.submitted_excerpt_document:
            return

        if not proposal_model.agenda_item:
            return

        # this must happen before moving the proposal document into the
        # meeting dossier as an event relies on the relation from proposal
        # to document when the word meeting flag is enabled
        document = proposal_model.submitted_excerpt_document.resolve_document()
        submitted_proposal.append_excerpt(document)

        meeting = proposal_model.agenda_item.meeting
        meeting_dossier = meeting.get_dossier()
        api.content.move(source=document, target=meeting_dossier, safe_id=True)

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


class AdHocAgendaItemMigrator(object):
    """Generate Word *.docx files for ad-hoc agenda items in the meeting
    dossier based on its fields and a sablon template.
    """
    def __init__(self, ad_hoc_template):
        self.normalizer = getUtility(IIDNormalizer)
        self.ad_hoc_template = ad_hoc_template

    def migrate(self, agenda_item):
        ad_hoc_document = self.generate_word_file(agenda_item)

        if not ad_hoc_document:
            return

        self.move_fields_to_annotations(agenda_item, ad_hoc_document)

    def generate_word_file(self, agenda_item):
        meeting_dossier = agenda_item.meeting.get_dossier()

        sablon = Sablon(self.ad_hoc_template)
        sablon.process(self.get_json_data(agenda_item))
        if sablon.is_processed_successfully():
            filename = u"{}.docx".format(
                self.normalizer.normalize(agenda_item.title))

            ad_hoc_document = CreateDocumentCommand(
                context=meeting_dossier,
                filename=filename,
                data=sablon.file_data,
                content_type=MIME_DOCX,
                title=agenda_item.title,
            ).execute()

            agenda_item.ad_hoc_document_oguid = Oguid.for_object(
                ad_hoc_document)
            return ad_hoc_document
        else:
            url = agenda_item.meeting.get_url(view='agenda_items/{}'.format(
                agenda_item.agenda_item_id))
            msg = 'Could not generate sablon document: "{}"'.format(url)
            logger.error(msg)
            logger.error(sablon.stderr)

        return None

    def move_fields_to_annotations(self, agenda_item, ad_hoc_document):
        """Remember old html field values in document's annotations.

        Then set field values to None to have the same state as if they were
        created with the word feature flag.
        """
        annotations = IAnnotations(ad_hoc_document)
        if LEGACY_DATA_KEY not in annotations:
            annotations[LEGACY_DATA_KEY] = PersistentDict()
        field_backup = annotations[LEGACY_DATA_KEY]

        field_backup['decision'] = agenda_item.decision
        field_backup['discussion'] = agenda_item.discussion

    def get_data(self, agenda_item):
        agenda_item_data = {}
        agenda_item_data['title'] = agenda_item.title
        agenda_item_data['html:decision'] = agenda_item.decision
        agenda_item_data['html:discussion'] = agenda_item.discussion

        root = {}
        root['mandant'] = {
            'name': get_current_admin_unit().title
        }
        # keep agenda items list for easier template reusability
        root['agenda_items'] = [agenda_item_data]
        return root

    def get_json_data(self, agenda_item):
        return json.dumps(self.get_data(agenda_item))


class MigrateToWordSPV(SQLUpgradeStep):
    """Migrate to word SPV.
    """
    def migrate(self):
        self.install_upgrade_profile()
        self.migrate_proposals()
        self.migrate_submitted_proposals()
        self.migrate_ad_hoc_proposals()
        self.remove_meeting_excerpts_relation()

    def migrate_proposals(self):
        """Generate word documents that contain the proposals fields."""
        proposal_template = UpgradeSablonTemplateWrapper(
            templates.load('template-proposal.docx'))
        migrator = ProposalMigrator(proposal_template)

        for proposal in self.objects(
                {'portal_type': 'opengever.meeting.proposal'},
                'Create proposal documents'):
            migrator.migrate(proposal)

    def migrate_submitted_proposals(self):
        """Generate word documents that contain the submitteed proposals
        fields.
        """
        submitted_proposal_template = UpgradeSablonTemplateWrapper(
            templates.load('template-submittedproposal.docx'))
        migrator = SubmittedProposalMigrator(submitted_proposal_template)

        for submitted_proposal in self.objects(
                {'portal_type': 'opengever.meeting.submittedproposal'},
                'Create submitted proposal documents'):
            migrator.migrate(submitted_proposal)

    def migrate_ad_hoc_proposals(self):
        ad_hoc_template = UpgradeSablonTemplateWrapper(
            templates.load('template-ad-hoc.docx'))
        migrator = AdHocAgendaItemMigrator(ad_hoc_template)

        query = AgendaItem.query.filter(
            AgendaItem.proposal_id==None, AgendaItem.is_paragraph==False)
        for agenda_item in query:
            migrator.migrate(agenda_item)

    def remove_meeting_excerpts_relation(self):
        """The functionality to generate generic excerpts for a meeting that
        could include multiple agenda items is no longer available.

        We won't loose information as the excerpt documents will still be in
        the meeting dossier. Tracking them sparately here is no longer
        necessary.
        """
        # find out which generated documents are meeting excerpts
        results = self.execute(
            select([meeting_excerpts.c.document_id])
        ).fetchall()
        ids_to_delete = set(itertools.chain(*results))

        # clear relation table
        self.execute(meeting_excerpts.delete())
        # remove generated documents that refer to meeting excerpts
        self.execute(
            generateddocuments_table.delete().where(
                generateddocuments_table.c.id.in_(ids_to_delete))
            )
