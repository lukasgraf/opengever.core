from opengever.base.browser.default_view import OGDefaultView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


class NoteView(OGDefaultView):
    """
    """
    template = ViewPageTemplateFile('templates/note.pt')
