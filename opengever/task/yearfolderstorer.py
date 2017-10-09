from Acquisition import aq_inner
from Acquisition import aq_parent
from opengever.base.security import elevated_privileges
from opengever.document.handlers import DISABLE_DOCPROPERTY_UPDATE_FLAG
from opengever.task.browser.accept.utils import get_current_yearfolder


class YearfolderStorer(object):

    def __init__(self, context):
        self.context = context

    def store_in_yearfolder(self):
        """Move the forwarding (adapted context) in the actual yearfolder."""

        inbox = aq_parent(aq_inner(self.context))
        yearfolder = get_current_yearfolder(inbox=inbox)

        self.context.REQUEST.set(DISABLE_DOCPROPERTY_UPDATE_FLAG, True)

        with elevated_privileges():
            clipboard = inbox.manage_cutObjects((self.context.getId(),))
            yearfolder.manage_pasteObjects(clipboard)
