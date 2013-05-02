from opengever.core.testing import OPENGEVER_FIXTURE
from opengever.core.testing import truncate_sql_tables
from opengever.ogds.base.interfaces import IClientConfiguration
from opengever.ogds.base.setuphandlers import _create_example_client, _create_example_user
from opengever.ogds.base.utils import create_session
from plone.app.testing import FunctionalTesting
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import TEST_USER_ID
from plone.registry.interfaces import IRegistry
from zope.component import getUtility


class BaseLayer(PloneSandboxLayer):

    defaultBases = (OPENGEVER_FIXTURE, )

    def setUpPloneSite(self, portal):
        session = create_session()
        _create_example_client(session, 'plone',
                              {'title': 'Plone',
                              'ip_address': '127.0.0.1',
                              'site_url': 'http://nohost/plone',
                              'public_url': 'http://nohost/plone',
                              'group': 'og_mandant1_users',
                              'inbox_group': 'og_mandant1_inbox'})


        _create_example_user(session, portal, TEST_USER_ID,{
          'firstname': 'Test',
          'lastname': 'User',
          'email': 'test.user@local.ch',
          'email2': 'test_user@private.ch'},
          ('og_mandant1_users','og_mandant1_inbox', 'og_mandant2_users'))

        # configure client ID
        registry = getUtility(IRegistry, context=portal)
        client = registry.forInterface(IClientConfiguration)
        client.client_id = u'plone'

    def tearDown(self):
        super(BaseLayer, self).tearDown()
        truncate_sql_tables()


OPENGEVER_ADV_SEARCH_FIXTURE = BaseLayer()
OPENGEVER_ADV_SEARCH_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(OPENGEVER_ADV_SEARCH_FIXTURE,), name="OpengeverAdvancedsearch:Functional")
