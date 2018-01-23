from opengever.repository import _
from plone.autoform.interfaces import IFormFieldProvider
from plone.supermodel import model
from zope import schema
from zope.interface import alsoProvides


class IResponsibleOrgUnit(model.Schema):

    model.fieldset(
        u'common',
        label=_(u'fieldset_common', default=u'Common'),
        fields=['responsible_org_unit'],
        )

    responsible_org_unit = schema.Choice(
        title=_(
            u'responsible_org_unit',
            default=u'Responsible organisation unit'),
        vocabulary='opengever.ogds.base.OrgUnitsVocabularyFactory',
        required=False,
        )


alsoProvides(IResponsibleOrgUnit, IFormFieldProvider)
