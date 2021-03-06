from BTrees.OOBTree import OOBTree
from datetime import datetime
from datetime import timedelta
from ftw.testing import freeze
from opengever.base.interfaces import IRecentlyTouchedSettings
from opengever.base.touched import ObjectTouchedEvent
from opengever.base.touched import RECENTLY_TOUCHED_KEY
from opengever.testing import IntegrationTestCase
from plone import api
from plone.uuid.interfaces import IUUID
from zope.annotation import IAnnotations
from zope.event import notify


FROZEN_NOW = datetime.now()


class TestObjectTouchedLogging(IntegrationTestCase):

    def setUp(self):
        super(TestObjectTouchedLogging, self).setUp()
        self._clear_recently_touched_mapping()

    def _clear_recently_touched_mapping(self):
        annotations = IAnnotations(self.portal)
        annotations.pop(RECENTLY_TOUCHED_KEY, None)

    def _get_log(self, user):
        annotations = IAnnotations(self.portal)
        recently_touched_mapping = annotations[RECENTLY_TOUCHED_KEY]
        recently_touched_log = recently_touched_mapping[user.id]
        return recently_touched_log

    def test_object_touched_event_writes_log(self):
        self.login(self.regular_user)

        with freeze(FROZEN_NOW):
            notify(ObjectTouchedEvent(self.document))

        annotations = IAnnotations(self.portal)

        self.assertIn(RECENTLY_TOUCHED_KEY, annotations)

        recently_touched_mapping = annotations[RECENTLY_TOUCHED_KEY]
        self.assertIsInstance(recently_touched_mapping, OOBTree)

        self.assertIn(self.regular_user.id, recently_touched_mapping)

        last_entry = recently_touched_mapping[self.regular_user.id][-1]
        self.assertEqual(
            {'last_touched': FROZEN_NOW, 'uid': IUUID(self.document)},
            last_entry)

    def test_object_touched_only_logs_tracked_types(self):
        self.login(self.regular_user)

        with freeze(FROZEN_NOW):
            notify(ObjectTouchedEvent(self.dossier))

        annotations = IAnnotations(self.portal)

        self.assertNotIn(RECENTLY_TOUCHED_KEY, annotations)

    def test_base_documents_are_tracked(self):
        self.login(self.regular_user)

        with freeze(FROZEN_NOW):
            notify(ObjectTouchedEvent(self.document))
            notify(ObjectTouchedEvent(self.mail))

        recently_touched_log = self._get_log(self.regular_user)

        expected = [
            {'last_touched': FROZEN_NOW,
             'uid': 'createemails00000000000000000001'},
            {'last_touched': FROZEN_NOW,
             'uid': 'createtreatydossiers000000000002'}]
        self.assertEqual(expected, recently_touched_log)

    def test_recently_touched_log_gets_sorted_on_write(self):
        self.login(self.regular_user)

        with freeze(FROZEN_NOW):
            notify(ObjectTouchedEvent(self.document))

        recently_touched_log = self._get_log(self.regular_user)

        recently_touched_log.extend([
            {'last_touched': datetime(1995, 1, 1), 'uid': '1'},
            {'last_touched': datetime(2010, 1, 1), 'uid': '3'},
            {'last_touched': datetime(2000, 1, 1), 'uid': '2'},
        ])

        with freeze(FROZEN_NOW + timedelta(hours=1)):
            notify(ObjectTouchedEvent(self.document))

        uid = IUUID(self.document)

        self.assertEqual([
            {'last_touched': FROZEN_NOW + timedelta(hours=1), 'uid': uid},
            {'last_touched': datetime(2010, 1, 1, 0, 0), 'uid': '3'},
            {'last_touched': datetime(2000, 1, 1, 0, 0), 'uid': '2'},
            {'last_touched': datetime(1995, 1, 1, 0, 0), 'uid': '1'}],
            recently_touched_log)

    def test_recently_touched_log_gets_deduplicated_on_write(self):
        self.login(self.regular_user)

        with freeze(FROZEN_NOW):
            notify(ObjectTouchedEvent(self.document))

        with freeze(FROZEN_NOW + timedelta(hours=1)):
            notify(ObjectTouchedEvent(self.document))

        recently_touched_log = self._get_log(self.regular_user)

        uid = IUUID(self.document)
        self.assertEqual(
            [{'last_touched': FROZEN_NOW + timedelta(hours=1), 'uid': uid}],
            recently_touched_log,
            'Recently Touched Log should only contain most recent entry '
            '(no duplicate UIDs)')

    def test_recently_touched_log_gets_rotated_on_write(self):
        self.login(self.regular_user)

        start = datetime(2018, 4, 30, 12, 45)
        # Touch a document to initialize the log
        with freeze(start):
            notify(ObjectTouchedEvent(self.document))

        recently_touched_log = self._get_log(self.regular_user)

        custom_limit = 5

        api.portal.set_registry_record(
            'limit', custom_limit, IRecentlyTouchedSettings)

        for i in range(custom_limit * 3):
            recently_touched_log.append(
                {'last_touched': start + timedelta(minutes=i), 'uid': str(i)})

        with freeze(FROZEN_NOW):
            notify(ObjectTouchedEvent(self.document))

        # Fetch the log again because it doesn't get rotated in place
        recently_touched_log = self._get_log(self.regular_user)

        self.assertEqual(custom_limit, len(recently_touched_log))

        expected = [
            {'last_touched': FROZEN_NOW, 'uid': 'createtreatydossiers000000000002'},  # noqa
            {'last_touched': datetime(2018, 4, 30, 12, 59), 'uid': '14'},
            {'last_touched': datetime(2018, 4, 30, 12, 58), 'uid': '13'},
            {'last_touched': datetime(2018, 4, 30, 12, 57), 'uid': '12'},
            {'last_touched': datetime(2018, 4, 30, 12, 56), 'uid': '11'},
        ]
        self.assertEqual(expected, recently_touched_log)

    def test_recently_touched_log_rotation_handles_checked_out_docs(self):
        self.login(self.regular_user)

        # Touch a document to initialize the log
        with freeze(FROZEN_NOW):
            notify(ObjectTouchedEvent(self.document))

        recently_touched_log = self._get_log(self.regular_user)

        limit = api.portal.get_registry_record(
            'limit', IRecentlyTouchedSettings)

        for i in range(limit * 3):
            recently_touched_log.append(
                {'last_touched': datetime.now(), 'uid': str(i)})

        self.checkout_document(self.subdocument)

        # Touch a document to trigger rotation
        with freeze(FROZEN_NOW):
            notify(ObjectTouchedEvent(self.document))

        # We should now end up with twice the display limit plus number of
        # checked out documents as the total number of items in the log

        # Fetch the log again because it doesn't get rotated in place
        recently_touched_log = self._get_log(self.regular_user)

        self.assertEqual(
            limit + 1,
            len(recently_touched_log))
