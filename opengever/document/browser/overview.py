from AccessControl import getSecurityManager
from five import grok
from opengever.base import _ as ogbmf
from opengever.base.browser import edit_public_trial
from opengever.base.browser.helper import get_css_class
from opengever.bumblebee import get_representation_url_by_object
from opengever.bumblebee import is_bumblebee_feature_enabled
from opengever.document import _
from opengever.document.browser.download import DownloadConfirmationHelper
from opengever.document.document import IDocumentSchema
from opengever.document.interfaces import ICheckinCheckoutManager
from opengever.dossier.base import DOSSIER_STATES_CLOSED
from opengever.meeting import is_meeting_feature_enabled
from opengever.meeting.model import SubmittedDocument
from opengever.ogds.base.actor import Actor
from opengever.tabbedview.browser.base import OpengeverTab
from plone import api
from plone.directives.dexterity import DisplayForm
from z3c.form.browser.checkbox import SingleCheckBoxWidget
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import queryMultiAdapter


try:
    from opengever.pdfconverter.behaviors.preview import IPreviewMarker
    from opengever.pdfconverter.behaviors.preview import IPreview

    PDFCONVERTER_AVAILABLE = True
except ImportError:
    PDFCONVERTER_AVAILABLE = False


class BaseRow(object):
    """Base class for metadata row configurations.
    """
    def __init__(self):
        self._view = None

    def bind(self, view):
        self._view = view

    @property
    def view(self):
        if self._view is None:
            raise Exception("Not bound to a view yet!")
        return self._view


class FieldRow(BaseRow):
    """A metadata row type that gets its information from schema fields.
    """
    def __init__(self, field, label=None):
        super(FieldRow, self).__init__()
        self.field = field
        self.label = label

    def __repr__(self):
        return "<%s for '%s'>" % (self.__class__.__name__, self.field)

    def available(self):
        return self.field in self.view.w

    def get_label(self):
        if self.label is not None:
            return self.label

        widget = self.view.w[self.field]
        if isinstance(widget, SingleCheckBoxWidget):
            label = widget.items[0]['label']
        else:
            label = widget.label
        return label

    def get_content(self):
        widget = self.view.w[self.field]
        if isinstance(widget, SingleCheckBoxWidget):
            content = self._render_boolean_field(widget)
        else:
            content = widget.render()
        return content

    def _render_boolean_field(self, widget):
        value = widget.items[0]['checked']
        yes = _('label_yes', default='yes')
        no = _('label_no', default='no')
        return bool(value) and yes or no


class CustomRow(BaseRow):
    """A custom metadata row type that uses a callable `renderer` to
    fetch the row's content.
    """
    def __init__(self, renderer, label):
        super(CustomRow, self).__init__()
        self.renderer = renderer
        self.label = label

    def available(self):
        return True

    def get_label(self):
        return self.label

    def get_content(self):
        return self.renderer()


class TemplateRow(CustomRow):
    """Row that renders a template.

    The parameter template_name should be the filename (without extension) of
    a template from the templates folder.
    """

    def __init__(self, template, label):
        self.template = template
        super(TemplateRow, self).__init__(self.template, label)

    def get_content(self):
        return self.renderer(self.view)


class Overview(DisplayForm, OpengeverTab):
    grok.context(IDocumentSchema)
    grok.name('tabbedview_view-overview')
    grok.template('overview')

    show_searchform = False

    file_template = ViewPageTemplateFile('templates/file.pt')
    public_trial_template = ViewPageTemplateFile('templates/public_trial.pt')
    submitted_with_template = ViewPageTemplateFile('templates/submitted_with.pt')

    def get_metadata_config(self):
        rows = [
            FieldRow('title'),
            FieldRow('IDocumentMetadata.document_date'),
            FieldRow('IDocumentMetadata.document_type'),
            FieldRow('IDocumentMetadata.document_author'),
            CustomRow(self.render_creator_link,
                      label=_('label_creator', default='creator')),
            FieldRow('IDocumentMetadata.description'),
            FieldRow('IDocumentMetadata.foreign_reference'),
            CustomRow(self.render_checked_out_link,
                      label=_('label_checked_out', default='Checked out')),
            TemplateRow(self.file_template,
                        label=_('label_file', default='File')),
            FieldRow('IDocumentMetadata.digitally_available'),
            FieldRow('IDocumentMetadata.preserved_as_paper'),
            FieldRow('IDocumentMetadata.receipt_date'),
            FieldRow('IDocumentMetadata.delivery_date'),
            FieldRow('IRelatedDocuments.relatedItems'),
            FieldRow('IClassification.classification'),
            FieldRow('IClassification.privacy_layer'),
            TemplateRow(self.public_trial_template,
                        label=ogbmf('label_public_trial',
                                    default='Public Trial')),
            FieldRow('IClassification.public_trial_statement'),
        ]
        if is_meeting_feature_enabled():
            rows.append(TemplateRow(self.submitted_with_template,
                                    label=_('Submitted with')))
        return rows

    def get_metadata_rows(self):
        for row in self.get_metadata_config():
            row.bind(self)
            if not row.available():
                continue
            data = dict(label=row.get_label(),
                        content=row.get_content())
            yield data

    def submitted_documents(self):
        return SubmittedDocument.query.by_source(self.context).all()

    def get_update_document_url(self, submitted_document):
        return '{}/@@submit_additional_document?submitted_document_id={}'.format(
            self.context.absolute_url(),
            submitted_document.document_id
        )

    def is_outdated(self, submitted_document):
        return not submitted_document.is_up_to_date(self.context)

    def render_submitted_version(self, submitted_document):
        return _(u"Submitted version: ${version}",
                 mapping={'version': submitted_document.submitted_version})

    def render_current_document_version(self):
        return _(u"Current version: ${version}",
                 mapping={'version': self.context.get_current_version()})

    def render_creator_link(self):
        return Actor.user(self.context.Creator()).get_link()

    def render_checked_out_link(self):
        manager = queryMultiAdapter(
            (self.context, self.request), ICheckinCheckoutManager)

        if manager.get_checked_out_by():
            return Actor.user(manager.get_checked_out_by()).get_link()
        return ''

    def get_css_class(self):
        return get_css_class(self.context)

    def is_preview_supported(self):
        # XXX TODO: should be persistent called two times
        if PDFCONVERTER_AVAILABLE:
            return IPreviewMarker.providedBy(self.context)
        return False

    def is_pdf_download_available(self):
        if self.is_preview_supported():
            return IPreview(self.context).is_downloadable

        return False

    def is_checkout_and_edit_available(self):
        manager = queryMultiAdapter(
            (self.context, self.request), ICheckinCheckoutManager)

        if manager.get_checked_out_by():
            if manager.get_checked_out_by() == \
                    getSecurityManager().getUser().getId():
                return True
            else:
                return False

        return manager.is_checkout_allowed()

    def is_download_copy_available(self):
        """Disable copy link when the document is checked
        out by an other user."""

        manager = queryMultiAdapter(
            (self.context, self.request), ICheckinCheckoutManager)
        if manager.get_checked_out_by():
            if manager.get_checked_out_by() != getSecurityManager().getUser().getId():
                return False
        return True

    def show_modfiy_public_trial_link(self):
        try:
            can_edit = edit_public_trial.can_access_public_trial_edit_form(
                getSecurityManager().getUser(),
                self.context)
        except (AssertionError, ValueError):
            return False

        state = api.content.get_state(self.context.get_parent_dossier())
        return can_edit and state in DOSSIER_STATES_CLOSED

    def get_download_copy_tag(self):
        dc_helper = DownloadConfirmationHelper()
        return dc_helper.get_html_tag(
            self.context.absolute_url(),
            additional_classes=['function-download-copy'],
            include_token=True
            )

    def show_preview(self):
        return is_bumblebee_feature_enabled()

    def get_preview_image_url(self):
        return get_representation_url_by_object('image', self.context)
