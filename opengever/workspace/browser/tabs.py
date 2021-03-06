from opengever.tabbedview.browser.tabs import Dossiers
from opengever.tabbedview.helper import linked
from opengever.tabbedview.helper import readable_ogds_author
from opengever.workspace import _


class Workspaces(Dossiers):

    filterlist_available = False
    major_actions = []
    enabled_actions = []

    columns = (

        {'column': 'reference',
         'column_title': _(u'label_reference', default=u'Reference Number'),
         'width': 120},

        {'column': 'Title',
         'column_title': _(u'label_title', default=u'Title'),
         'sort_index': 'sortable_title',
         'transform': linked,
         'width': 500},

        {'column': 'responsible',
         'column_title': _(u'label_dossier_responsible',
                           default=u"Responsible"),
         'transform': readable_ogds_author,
         'width': 300}
    )
