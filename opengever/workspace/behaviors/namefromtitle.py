from opengever.dossier.behaviors import dossiernamefromtitle
from plone.app.content.interfaces import INameFromTitle
from zope.interface import implements


class IWorkspaceNameFromTitle(INameFromTitle):
    """Behavior interface.
    """


class WorkspaceNameFromTitle(dossiernamefromtitle.DossierNameFromTitle):
    """Special name from title behavior for letting the normalizing name
    chooser choose the ID like want it to be.
    The Id of a workspace should be in the format:
        'workspace-{sequence number}'
    """
    implements(IWorkspaceNameFromTitle)

    format = u'workspace-%i'


class IWorkspaceFolderNameFromTitle(INameFromTitle):
    """ Behavior interface.
    """


class WorkspaceFolderNameFromTitle(dossiernamefromtitle.DossierNameFromTitle):
    """ The ID of a workspace folder should be 'folder-{sequence number}'.
    """
    implements(IWorkspaceFolderNameFromTitle)

    format = u'folder-%i'
