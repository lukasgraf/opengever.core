from opengever.dossier import _
from opengever.advancedsearch.advanced_search import AdvancedSearchForm
from opengever.advancedsearch.advanced_search import IAdvancedSearch
from plone.supermodel import model
from plone.z3cform.fieldsets.utils import move
from zope import schema


class IFilingnumberSearchAddition(model.Schema):

    searchable_filing_no = schema.TextLine(
        title=_('label_filing_number', default='Filing number'),
        description=_('help_filing_number', default=''),
        required=False,
    )


class FilingAdvancedSearchForm(AdvancedSearchForm):

    schemas = (IAdvancedSearch, IFilingnumberSearchAddition)

    def move_fields(self):
        move(self, 'searchable_filing_no', before='responsible')

    def field_mapping(self):
        """Append searchable_filing_no to default field mappings"""

        mapping = super(FilingAdvancedSearchForm, self).field_mapping()
        dossier_fields = mapping.get(
            'opengever-dossier-behaviors-dossier-IDossierMarker')

        if 'searchable_filing_no' not in dossier_fields:
            dossier_fields.insert(
                dossier_fields.index('responsible'), 'searchable_filing_no')

        return mapping
