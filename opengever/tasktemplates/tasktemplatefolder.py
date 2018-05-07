from datetime import date
from datetime import timedelta
from opengever.dossier.behaviors.dossier import IDossier
from opengever.ogds.base.utils import get_current_org_unit
from opengever.task.activities import TaskAddedActivity
from opengever.task.interfaces import ITaskSettings
from opengever.tasktemplates.content.templatefoldersschema import sequence_types
from opengever.tasktemplates.interfaces import IFromTasktemplateGenerated
from plone import api
from plone.dexterity.content import Container
from plone.dexterity.utils import addContentToContainer
from plone.dexterity.utils import createContent
from zope.event import notify
from zope.globalrequest import getRequest
from zope.interface import alsoProvides
from zope.lifecycleevent import ObjectCreatedEvent


class TaskTemplateFolder(Container):

    @property
    def sequence_type_label(self):
        return sequence_types.by_value[self.sequence_type].title

    def trigger(self, dossier, templates, related_documents,
                values, start_immediately=True):

        trigger = TaskTemplateFolderTrigger(dossier, templates, related_documents,
                                  values, start_immediately)
        main_task = trigger.create_main_task()
        trigger.create_subtasks(main_task, templates, related_documents)


class TaskTemplateFolderTrigger(object):

    def __init__(self, dossier, templates,
                 related_documents, values, start_immediately):
        self.dossier = dossier
        self.selected_templates = templates
        self.related_documents = related_documents
        self.values = values
        self.start_immediately = start_immediately

    def add_task(self, container, data):
        task = createContent('opengever.task.task', **data)
        notify(ObjectCreatedEvent(task))
        task = addContentToContainer(container, task, checkConstraints=True)
        self.mark_as_generated_from_tasktemplate(task)
        return task

    def create_main_task(self):
        data = dict(
            title=self.context.title,
            issuer=api.user.get_current().getId(),
            responsible=api.user.get_current().getId(),
            responsible_client=get_current_org_unit().id(),
            task_type='direct-execution',
            deadline=self.get_main_task_deadline())

        main_task = self.add_task(self.dossier, data)

        # set the main_task in to the in progress state
        api.content.transition(obj=main_task,
                               transition='task-transition-open-in-progress')

        return main_task

    def create_subtasks(self, main_task):

        for template in self.selected_templates:
            self.create_subtask(
                main_task, template, self.values.get(template.id))

    def create_subtask(self, main_task, template, values):
        data = dict(
            title=template.title,
            issuer=template.issuer,
            responsible=template.responsible,
            responsible_client=template.responsible_client,
            task_type=template.task_type,
            text=template.text,
            relatedItems=related_documents,
            deadline=date.today() + timedelta(template.deadline),
        )

        data.update(values)
        self.replace_interactive_actors(data)

        task = self.add_task(main_task, data)
        task.reindexObject()

        # add activity record for subtask
        activity = TaskAddedActivity(task, getRequest(), main_task)
        activity.record()

    def get_main_task_deadline(self):
        highest_deadline = max(
            [template.deadline for template in self.selected_templates])
        deadline_timedelta = api.portal.get_registry_record(
            'deadline_timedelta', interface=ITaskSettings)
        return date.today() + timedelta(highest_deadline + deadline_timedelta)

    def mark_as_generated_from_tasktemplate(self, task):
        alsoProvides(task, IFromTasktemplateGenerated)

    def replace_interactive_actors(self, data):
        data['issuer'] = self.get_interactive_represent(data['issuer'])
        if data['responsible_client'] == 'interactive_users':
            data['responsible_client'] = get_current_org_unit().id()
            data['responsible'] = self.get_interactive_represent(
                data['responsible'])

    def get_interactive_represent(self, principal):
        """The current systems knows two interactive users:

        `responsible`: the reponsible of the main dossier.
        `current_user`: the currently logged in user.
        """

        if principal == 'responsible':
            return IDossier(self.dossier.get_main_dossier()).responsible

        elif principal == 'current_user':
            return api.user.get_current().getId()

        else:
            return principal
