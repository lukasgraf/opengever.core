from five import grok

from zope.annotation.interfaces import IAnnotations
from persistent.dict import PersistentDict
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleVocabulary
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone import PloneMessageFactory as PMF
from ftw.task import _


class UsersVocabulary(SimpleVocabulary):
    def search(self, query_string):
        return [v for v in self if query_string.lower() in v.value.lower()]

@grok.provider(IContextSourceBinder)
def getManagersVocab(context):

    acl_users = getToolByName(context, 'acl_users')
    terms = []
    if acl_users is not None:
        for user in acl_users.getUsers():
            member_name = user.getProperty('fullname') or user.getName()
            member_name = member_name + "  " + user.getProperty('email') or member_name

            terms.append(SimpleVocabulary.createTerm(user.getId(), str(user.getId()), member_name))
    return UsersVocabulary(terms)

@grok.provider(IContextSourceBinder)
def getTransitionVocab(context):
    wftool = getToolByName(context, 'portal_workflow')
    transitions = []
    for tdef in wftool.getTransitionsFor(context):
        transitions.append(SimpleVocabulary.createTerm(tdef['id'],tdef['id'],PMF(tdef['id'], default=tdef['title_or_id'])))
    return SimpleVocabulary(transitions)

def create_sequence_number( obj, key='task_sequence_number' ):
    portal = obj.portal_url.getPortalObject()
    portal_annotations = IAnnotations( portal )
    sequence_number = int(portal_annotations.get(key, 0)) + 1
    portal_annotations[key] = sequence_number
    return sequence_number