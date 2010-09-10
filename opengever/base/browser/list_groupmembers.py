from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


class ListGroupMembers(BrowserView):
    template = ViewPageTemplateFile("list_groupmembers.pt")
    def __call__(self):
        group_id = self.context.REQUEST.get('group', None)
        if not group_id:
            return 'no group id'
        groups_tool = self.context.portal_groups
        group = groups_tool.getGroupById(group_id)
        self.group_name = group.title or group.id
        self.members = group.getAllGroupMembers()
        return self.template()