from collective import dexteritytextindexer
from opengever.base.source import DossierPathSourceBinder
from opengever.base.widgets import TrixFieldWidget
from opengever.document import _
from opengever.document.base import BaseDocumentMixin
from opengever.ogds.base.autocomplete_widget import AutocompleteMultiFieldWidget
from plone.dexterity.content import Container
from plone.directives import form
from z3c.relationfield.schema import RelationChoice
from z3c.relationfield.schema import RelationList
from zope import schema


class INoteSchema(form.Schema):

    form.fieldset(
        u'common',
        label=_(u'fieldset_common', u'Common'),
        fields=[
            u'title',
            u'date',
            u'note',
            u'related_participations',
            u'related_documents',
        ]
    )

    dexteritytextindexer.searchable('title')
    title = schema.TextLine(
        title=_(u'label_title', default=u'Title'),
        required=True
    )

    date = schema.Date(
        title=_(u'label_date', default=u'Date'),
        required=True
    )

    dexteritytextindexer.searchable('note')
    form.widget(note=TrixFieldWidget)
    note = schema.Text(
        title=_(u'label_note', default=u'Note'),
        required=False
    )

    form.widget(related_participations=AutocompleteMultiFieldWidget)
    related_participations = schema.Tuple(
        title=_(u'label_participations', default=u'Participations'),
        value_type=schema.Choice(
            title=u'participations',
            source=u'opengever.ogds.base.ContactsAndUsersVocabulary'),
        required=False,
        missing_value=(),  # important!
        default=(),
    )

    related_documents = RelationList(
        title=_(u'label_related_documents', default=u'Related documents'),
        default=[],
        missing_value=[],
        value_type=RelationChoice(
            title=u"Related",
            source=DossierPathSourceBinder(
                portal_type=("opengever.document.document",
                             "opengever.document.note",
                             "ftw.mail.mail"),
                navigation_tree_query={
                    'object_provides':
                    ['opengever.dossier.behaviors.dossier.IDossierMarker',
                     'opengever.document.document.IDocumentSchema',
                     'opengever.task.task.ITask',
                     'ftw.mail.mail.IMail', ],
                }),
            ),
        required=False,
    )


class Note(Container, BaseDocumentMixin):
    """Class for the note type.
    """
