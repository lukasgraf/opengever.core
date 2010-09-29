from opengever.ogds.base.interfaces import IClientConfiguration
from opengever.ogds.base.setuphandlers import create_sql_tables, MODELS
from opengever.ogds.base.utils import create_session
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import applyProfile
from plone.dexterity import utils
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.configuration import xmlconfig



def create_contacts(portal):
    """Creates a bunch of contacts for testing with.
    """
    # create contact folder
    if 'contacts' not in portal.objectIds():
        contacts = utils.createContentInContainer(
            portal,
            'opengever.contact.contactfolder',
            checkConstraints=False,
            title='Contacts')
        assert 'contacts' in portal.objectIds(), \
            'Could not create contacts folder'
        contacts.reindexObject()
    else:
        contacts = portal.contacts

    contact_list = (
        ('Sandra', 'Kaufmann', 'sandra.kaufmann@test.ch'),
        ('Elisabeth', u'K\xe4ppeli'.encode('utf8'),
         'elisabeth.kaeppeli@test.ch'),
        ('Roger', 'Wermuth', 'roger.wermuth@test.ch'))

    for firstname, lastname, email in contact_list:
        obj = utils.createContentInContainer(
            contacts,
            'opengever.contact.contact',
            checkConstraints=False,
            firstname=firstname,
            lastname=lastname,
            email=email)
        obj.reindexObject()



class BaseLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE, )

    def setUpZope(self, app, configurationContext):
        # do not install pas plugins (doesnt work in tests)
        from opengever.ogds.base import setuphandlers
        setuphandlers.setup_scriptable_plugin = lambda *a, **kw: None
        # Load configure.zcml
        import opengever.ogds.base
        xmlconfig.file('configure.zcml', opengever.ogds.base,
                       context=configurationContext)
        xmlconfig.file('tests.zcml', opengever.ogds.base,
                       context=configurationContext)

    def setUpPloneSite(self, portal):
        # Install into Plone site using portal_setup
        applyProfile(portal, 'plone.app.registry:default')
        applyProfile(portal, 'opengever.contact:default')
        applyProfile(portal, 'opengever.ogds.base:default')
        # configure client ID
        registry = getUtility(IRegistry, context=portal)
        client = registry.forInterface(IClientConfiguration)
        client.client_id = u'client1'
        # portal workaround
        self.portal = portal

    def testSetUp(self):
        # setup the sql tables
        create_sql_tables()

    def testTearDown(test):
        session = create_session()
        for model in MODELS:
            getattr(model, 'metadata').drop_all(session.bind)
        # we may have created custom users and


OPENGEVER_OGDS_BASE_FIXTURE = BaseLayer()
OPENGEVER_OGDS_BASE_TESTING = IntegrationTesting(
    bases=(OPENGEVER_OGDS_BASE_FIXTURE,), name="OpengeverOgdsBase:Integration")
