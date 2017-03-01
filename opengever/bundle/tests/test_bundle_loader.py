from opengever.bundle.loader import BundleLoader
from opengever.bundle.loader import IngestionSettingsReader
from opengever.bundle.loader import ItemPreprocessor
from opengever.bundle.tests.helpers import get_portal_type
from opengever.bundle.tests.helpers import get_title
from pkg_resources import resource_filename as rf
from unittest2 import TestCase
import jsonschema
import tempfile


def get_bundle_path(bundle_name):
    return rf('opengever.bundle.tests', 'assets/%s' % bundle_name)


class TestBundleLoader(TestCase):

    def load_bundle(self, bundle_path=None):
        if not bundle_path:
            bundle_path = get_bundle_path('basic.oggbundle')
        loader = BundleLoader(bundle_path)
        bundle = loader.load()
        return bundle

    def test_loads_configuration(self):
        bundle = self.load_bundle()
        self.assertEqual({}, bundle.configuration)

    def test_loads_correct_number_of_items(self):
        bundle = self.load_bundle()
        self.assertEqual(10, len(list(bundle)))

    def test_loads_items_in_correct_order(self):
        bundle = self.load_bundle()
        self.assertEqual(
            [('repositoryroot', u'Ordnungssystem'),
             ('repositoryfolder', u'Personal'),
             ('repositoryfolder', u'Organigramm, Prozesse'),
             ('repositoryfolder', u'Organisation'),
             ('businesscasedossier', u'Dossier Vreni Meier'),
             ('businesscasedossier', u'Hanspeter M\xfcller'),
             ('document', u'Bewerbung Hanspeter M\xfcller'),
             ('document', u'Entlassung Hanspeter M\xfcller'),
             ('mail', u'Ein Mail'),
             ('document', u'Document referenced via UNC-Path')],
            [(get_portal_type(i), get_title(i)) for i in list(bundle)])

    def test_inserts_portal_type(self):
        bundle = self.load_bundle()
        self.assertEqual([
            ('businesscasedossier', u'Dossier Vreni Meier'),
            ('businesscasedossier', u'Hanspeter M\xfcller'),
            ('document', u'Bewerbung Hanspeter M\xfcller'),
            ('document', u'Document referenced via UNC-Path'),
            ('document', u'Entlassung Hanspeter M\xfcller'),
            ('mail', u'Ein Mail'),
            ('repositoryfolder', u'Organigramm, Prozesse'),
            ('repositoryfolder', u'Organisation'),
            ('repositoryfolder', u'Personal'),
            ('repositoryroot', u'Ordnungssystem')],
            sorted([(get_portal_type(i), get_title(i)) for i in list(bundle)]))

    def test_validates_schemas(self):
        bundle_path = get_bundle_path('schema_violation.oggbundle')

        with self.assertRaises(jsonschema.ValidationError):
            self.load_bundle(bundle_path)

    def test_skips_missing_files_gracefully(self):
        bundle = self.load_bundle(get_bundle_path('partial.bundle'))
        self.assertEqual(1, len(list(bundle)))


class TestItemPreprocessor(TestCase):

    def test_strips_extension_from_title(self):
        item = {'title': 'foo.txt', 'filepath': '/file1.txt'}
        ItemPreprocessor(item, 'documents.json').process()
        self.assertEqual('foo', item['title'])

    def test_strips_extension_from_title_but_keeps_original_filename(self):
        item = {'title': 'foo.txt', 'filepath': '/file1.txt'}
        ItemPreprocessor(item, 'documents.json').process()
        self.assertEqual('foo.txt', item['_original_filename'])

    def test_doesnt_strip_non_extension(self):
        item = {'title': 'Position 1.2.3', 'filepath': '/file1.txt'}
        ItemPreprocessor(item, 'documents.json').process()
        self.assertEqual('Position 1.2.3', item['title'])

    def test_sets_portal_type_based_on_json_name_by_default(self):
        item = {}
        ItemPreprocessor(item, 'reporoots.json').process()
        expected = 'opengever.repository.repositoryroot'
        self.assertEqual(expected, item['_type'])

        item = {}
        ItemPreprocessor(item, 'repofolders.json').process()
        expected = 'opengever.repository.repositoryfolder'
        self.assertEqual(expected, item['_type'])

        item = {}
        ItemPreprocessor(item, 'dossiers.json').process()
        expected = 'opengever.dossier.businesscasedossier'
        self.assertEqual(expected, item['_type'])

        item = {'filepath': 'regular_document.docx', 'title': ''}
        ItemPreprocessor(item, 'documents.json').process()
        expected = 'opengever.document.document'
        self.assertEqual(expected, item['_type'])

    def test_sets_portal_type_for_mails(self):
        item = {'filepath': 'mail.eml', 'title': ''}
        ItemPreprocessor(item, 'documents.json').process()
        expected = 'ftw.mail.mail'
        self.assertEqual(expected, item['_type'])

    def test_drops_review_state_for_items_with_one_state_workflows(self):
        item = {
            'title': 'My document',
            'filepath': '/mydoc.docx',
            'review_state': 'document-state-draft'
        }
        ItemPreprocessor(item, 'documents.json').process()
        self.assertNotIn('review_state', item)


class TestIngestionSettingsReader(TestCase):

    def setUp(self):
        super(TestIngestionSettingsReader, self).setUp()

    def test_loads_settings_from_json_file(self):
        with tempfile.NamedTemporaryFile() as settings_file:
            settings_file.write('{}')
            settings_file.flush()

            reader = IngestionSettingsReader(settings_file.name)
            settings = reader()
            self.assertEqual({}, settings)

    def test_doesnt_fail_if_settings_file_doesnt_exist(self):
        reader = IngestionSettingsReader('/missing/directory/file.json')
        settings = reader()
        self.assertEqual({}, settings)