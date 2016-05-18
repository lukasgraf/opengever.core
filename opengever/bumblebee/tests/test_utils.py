from ftw.builder import Builder
from ftw.builder import create
from ftw.bumblebee.tests.helpers import asset as bumblebee_asset
from opengever.bumblebee import get_representation_url_by_brain
from opengever.bumblebee import get_representation_url_by_object
from opengever.bumblebee import is_bumblebee_feature_enabled
from opengever.bumblebee import is_bumblebeeable
from opengever.bumblebee.interfaces import IGeverBumblebeeSettings
from opengever.testing import FunctionalTestCase
from opengever.testing import obj2brain
from plone import api


class TestIsBumblebeeFeatureEnabled(FunctionalTestCase):

    def test_true_if_registry_entry_is_true(self):
        api.portal.set_registry_record(
            'is_feature_enabled', True, interface=IGeverBumblebeeSettings)

        self.assertTrue(is_bumblebee_feature_enabled())

    def test_false_if_registry_entry_is_false(self):
        api.portal.set_registry_record(
            'is_feature_enabled', False, interface=IGeverBumblebeeSettings)

        self.assertFalse(is_bumblebee_feature_enabled())


class TestGetRepresentationUrlByObject(FunctionalTestCase):

    def test_returns_representation_url_if_checksum_is_available(self):
        document = create(Builder('document')
                          .attach_file_containing(
                              bumblebee_asset('example.docx').bytes(),
                              u'example.docx'))

        self.assertIn(
            '/YnVtYmxlYmVl/api/v3/resource/',
            get_representation_url_by_object('thumbnail', document))

    def test_returns_not_digitally_available_placeholder_image_if_no_ckecksum_is_available(self):
        document = create(Builder('document'))

        self.assertIn(
            'not_digitally_available.png',
            get_representation_url_by_object('thumbnail', document))


class TestGetRepresentationUrlByBrain(FunctionalTestCase):

    def test_returns_representation_url_if_checksum_is_available(self):
        document = create(Builder('document')
                          .attach_file_containing(
                              bumblebee_asset('example.docx').bytes(),
                              u'example.docx'))

        brain = obj2brain(document)

        self.assertIn(
            '/YnVtYmxlYmVl/api/v3/resource/',
            get_representation_url_by_brain('thumbnail', brain))

    def test_returns_not_digitally_available_placeholder_image_if_no_ckecksum_is_available(self):
        document = create(Builder('document'))

        brain = obj2brain(document)

        self.assertIn(
            'not_digitally_available.png',
            get_representation_url_by_brain('thumbnail', brain))


def TestIsBumblebeeable(FunctionalTestCase):

    def test_documents_are_bumblebeeable(self):
        document = create(Builder('document').with_dummy_content())
        brain = obj2brain(document)

        self.assertTrue(is_bumblebeeable(brain))

    def test_dossiers_are_not_bumblebeeable(self):
        document = create(Builder('dossier'))
        brain = obj2brain(document)

        self.assertFalse(is_bumblebeeable(brain))

    def test_mails_are_not_bumblebeeable(self):
        document = create(Builder('mail'))
        brain = obj2brain(document)

        self.assertFalse(is_bumblebeeable(brain))

    def test_repositories_are_not_bumblebeeable(self):
        document = create(Builder('repository'))
        brain = obj2brain(document)

        self.assertFalse(is_bumblebeeable(brain))

    def test_repo_roots_are_not_bumblebeeable(self):
        document = create(Builder('repository_root'))
        brain = obj2brain(document)

        self.assertFalse(is_bumblebeeable(brain))
