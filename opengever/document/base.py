from Acquisition import aq_base
from Acquisition import aq_inner
from Acquisition import aq_parent
from opengever.base.browser.helper import get_css_class
from opengever.dossier.behaviors.dossier import IDossierMarker
from opengever.dossier.dossiertemplate.behaviors import IDossierTemplateMarker
from opengever.dossier.templatefolder.interfaces import ITemplateFolder
from opengever.inbox.inbox import IInbox
from opengever.meeting.model.generateddocument import GeneratedExcerpt
from opengever.meeting.proposal import IProposal
from opengever.task.task import ITask
from plone import api
from plone.dexterity.content import Item
from Products.CMFCore.utils import getToolByName
from Products.MimetypesRegistry.common import MimeTypeException
from Products.MimetypesRegistry.interfaces import IMimetype
from zc.relation.interfaces import ICatalog
from zope.component import getUtility
from zope.intid.interfaces import IIntIds
import logging


LOG = logging.getLogger('opengever.document')


class BaseDocumentMixin(object):
    """Abstract base class for document-ish content types."""

    removed_state = None
    active_state = None

    remove_transition = None
    restore_transition = None

    def css_class(self):
        return get_css_class(self)

    def get_parent_dossier(self):
        """Return the document's parent dossier.

        A parent dossier is available for documents in a dossier/subdossier
        or for documents in a task.

        No parent dossier is available for documents in an inbox, in a
        forwarding or inside a proposal. In that case this method returns None.

        """
        parent = aq_parent(aq_inner(self))
        if IDossierMarker.providedBy(parent) or \
           IDossierTemplateMarker.providedBy(parent) or \
           ITemplateFolder.providedBy(parent):
            return parent
        if ITask.providedBy(parent):
            return parent.get_containing_dossier()
        if IProposal.providedBy(parent):
            return parent.get_containing_dossier()

        return None

    def get_parent_inbox(self):
        """Return the document's parent inbox or None."""
        parent = aq_parent(aq_inner(self))
        if IInbox.providedBy(parent):
            return parent

        return None

    def get_proposal(self):
        """Return the proposal to which this document belongs.

        This may return a "proposal" or a "submitted proposal".
        """
        parent = aq_parent(aq_inner(self))
        if IProposal.providedBy(parent):
            return parent

        # Find submitted proposal when self is an excerpt document in the
        # meeting dossier.
        for relation in getUtility(ICatalog).findRelations({
                'to_id': getUtility(IIntIds).getId(aq_inner(self)),
                'from_attribute': 'excerpts'}):
            # We expect that there are 0 or 1 relation, because this document
            # cannot be the excerpt of multiple proposals.
            submitted_proposal = relation.from_object
            if api.user.has_permission('View', obj=submitted_proposal):
                return submitted_proposal

        # Find proposal when self is an excerpt in the case dossier.
        generated_excerpts = GeneratedExcerpt.query.by_document(self).all()
        if generated_excerpts:
            proposal = generated_excerpts[0].proposal.resolve_proposal()
            if api.user.has_permission('View', obj=proposal):
                return proposal

        return None

    @property
    def is_removed(self):
        return api.content.get_state(obj=self) == self.removed_state

    @property
    def is_mail(self):
        return False

    def related_items(self):
        raise NotImplementedError

    def checked_out_by(self):
        raise NotImplementedError

    def get_current_version_id(self):
        raise NotImplementedError

    def get_filename(self):
        raise NotImplementedError

    def get_file(self):
        raise NotImplementedError

    def surrender(self, relative_to_portal=1):
        return Item.getIcon(self, relative_to_portal=relative_to_portal)

    def get_mimetype_icon(self, relative_to_portal=1):
        """Calculate the icon using the mime type of the file
        """
        utool = getToolByName(self, 'portal_url')

        mimetypeitem = self.get_mimetype()
        if not mimetypeitem:
            return self.surrender(relative_to_portal)

        icon = mimetypeitem[0].icon_path

        if relative_to_portal:
            return icon
        else:
            # Relative to REQUEST['BASEPATH1']
            res = utool(relative=1) + '/' + icon
            while res[:1] == '/':
                res = res[1:]
            return res

    def get_mimetype(self):
        """Return the mimetype as object. If there is no matching mimetype,
        it returns False.
        """
        mtr = getToolByName(self, 'mimetypes_registry', None)

        field = self.file
        if not field or not field.getSize():
            # there is no file
            return False

        # get icon by content type
        contenttype = field.contentType
        mimetypeitem = None
        try:
            mimetypeitem = mimetype_lookup(mtr, contenttype)
        except MimeTypeException, msg:
            LOG.error(
                'MimeTypeException for %s. Error is: %s' % (
                    self.absolute_url(), str(msg)))
        if not mimetypeitem:
            # not found
            return False
        return mimetypeitem


def mimetype_lookup(mtr, contenttype):
    """Reimplemented as case insensitive from Products.MimetypesRegistry."""
    __traceback_info__ = (repr(contenttype), str(contenttype))
    mapping = mtr._mimetypes
    contenttype = contenttype.lower()
    if IMimetype.providedBy(contenttype):
        return (aq_base(contenttype), )
    try:
        major, minor = contenttype.split('/', 1)
    except ValueError:
        raise MimeTypeException('Malformed MIME type ({})'.format(contenttype))
    mapping = {k.lower(): v for k, v in mapping.items()}
    group = {k.lower(): v for k, v in mapping.get(major, {}).items()}
    if not minor or minor == '*':
        res = group.values()
    else:
        res = group.get(minor)
        if res:
            res = (res,)
        else:
            return ()
    return tuple(aq_base(mtitem) for mtitem in res)
