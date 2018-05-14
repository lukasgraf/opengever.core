from ftw.builder import Builder
from ftw.builder import create
from ftw.solr.connection import SolrResponse
from ftw.solr.interfaces import ISolrSearch
from ftw.solr.schema import SolrSchema
from ftw.testbrowser import browsing
from mock import MagicMock
from opengever.base.source import DossierPathSourceBinder
from opengever.base.source import RepositoryPathSourceBinder
from opengever.testing import FunctionalTestCase
from opengever.testing import IntegrationTestCase
from zope.component import getUtility
import os.path


class TestRepositoryPathSourceBinder(FunctionalTestCase):

    def setUp(self):
        super(TestRepositoryPathSourceBinder, self).setUp()
        self.grant('Administrator', 'Contributor', 'Editor', 'Reader')

        self.reporoot_1 = create(Builder('repository_root')
                                 .titled(u'Ordnungssystem1'))
        self.repofolder1 = create(Builder('repository')
                                  .within(self.reporoot_1))
        self.repofolder1_1 = create(Builder('repository')
                                    .within(self.repofolder1))

        self.reporoot2 = create(Builder('repository_root')
                                 .titled(u'Ordnungssystem2'))
        self.repofolder2 = create(Builder('repository').within(self.reporoot2))

    def test_navigation_tree_query_is_limited_to_current_repository(self):
        source_binder = RepositoryPathSourceBinder()
        source = source_binder(self.repofolder1_1)
        self.assertEqual({'query': '/plone/ordnungssystem1'},
                         source.navigation_tree_query['path'])
        source = source_binder(self.repofolder1)
        self.assertEqual({'query': '/plone/ordnungssystem1'},
                         source.navigation_tree_query['path'])


class TestDossierSourceBinder(FunctionalTestCase):

    def test_only_objects_inside_the_maindossier_are_selectable(self):
        dossier_1 = create(Builder('dossier'))
        sub = create(Builder('dossier').within(dossier_1))
        dossier_2 = create(Builder('dossier'))
        create(Builder('document').titled(u'Test 1').within(dossier_1))
        create(Builder('document').titled(u'Test 2').within(dossier_2))

        source_binder = DossierPathSourceBinder(
            portal_type=("opengever.document.document", "ftw.mail.mail"),
            navigation_tree_query={
                'object_provides':
                ['opengever.dossier.behaviors.dossier.IDossierMarker',
                 'opengever.document.document.IDocumentSchema',
                 'opengever.task.task.ITask',
                 'ftw.mail.mail.IMail']}
        )

        source = source_binder(dossier_1)
        self.assertEqual(
            ['Test 1'], [term.title for term in source.search('Test')])

        source = source_binder(sub)
        self.assertEqual(
            ['Test 1'], [term.title for term in source.search('Test')])


class TestSolrObjPathSourceBinder(IntegrationTestCase):

    @browsing
    def test_related_dossier_autocomplete_uses_solr_when_feature_enabled(self, browser):
        self.activate_feature('solr')
        self.solr = self.mock_solr('solr_autocomplete.json')

        self.login(self.dossier_responsible, browser)
        browser.open(self.dossier, view='@@edit/++widget++form.widgets.IDossier.relatedDossier/@@autocomplete-search?q=empty')
        self.assertEqual('/plone/ordnungssystem/fuhrung/vertrage-und-vereinbarungen/dossier-6|An empty dossier',
                         browser.contents)

        self.solr.search.assert_called_with(
            query=u'{!boost b=recip(ms(NOW,modified),3.858e-10,10,1)}'
                  u'Title:empty^100 OR Title:empty*^20 OR SearchableText:empty^5 '
                  u'OR SearchableText:empty* OR metadata:empty^10 OR '
                  u'metadata:empty*^2 OR sequence_number_string:empty^2000',
            rows=20,
            fl=['path'],
            filters=[u'object_provides:opengever.dossier.behaviors.dossier.IDossierMarker']
        )

    @browsing
    def test_related_dossier_autocomplete_uses_catalog_when_solr_disabled(self, browser):
        self.login(self.dossier_responsible, browser)
        browser.open(self.dossier, view='@@edit/++widget++form.widgets.IDossier.relatedDossier/@@autocomplete-search?q=empty')
        self.assertEqual('/plone/ordnungssystem/fuhrung/vertrage-und-vereinbarungen/dossier-6|An empty dossier',
                         browser.contents)
