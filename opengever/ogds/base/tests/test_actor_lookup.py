from ftw.builder import Builder
from ftw.builder import create
from opengever.ogds.base.actor import Actor
from opengever.testing import FunctionalTestCase
from plone.app.testing import TEST_USER_ID
import unittest


class TestActorLookup(FunctionalTestCase):

    def setUp(self):
        super(TestActorLookup, self).setUp()
        self.grant('Reader', 'Contributor')

    def test_null_actor(self):
        actor = Actor.lookup('not-existing')

        self.assertEqual('not-existing', actor.get_label())
        self.assertIsNone(actor.get_profile_url())
        self.assertEqual('not-existing', actor.get_link())

    def test_inbox_actor_lookup(self):
        create(Builder('org_unit').id('foobar').having(title='Huhu'))
        actor = Actor.lookup('inbox:foobar')

        self.assertEqual('Inbox: Huhu', actor.get_label())
        self.assertIsNone(actor.get_profile_url())
        self.assertEqual('Inbox: Huhu', actor.get_link())

    def test_contact_actor_lookup(self):
        contact = create(Builder('contact')
                         .having(firstname=u'Hanspeter',
                                 lastname=u'Blahbla',
                                 email='h@example.com')
                         .in_state('published'))
        actor = Actor.lookup('contact:{}'.format(contact.id))
        self.assertEqual('Blahbla Hanspeter (h@example.com)',
                         actor.get_label())
        self.assertEqual(contact.absolute_url(), actor.get_profile_url())

        link = actor.get_link()
        self.assertIn(actor.get_label(), link)
        self.assertIn(actor.get_profile_url(), link)

    def test_user_actor_ogds_user(self):
        create(Builder('fixture'))
        create(Builder('ogds_user')
               .id('hugo.boss')
               .having(firstname='H\xc3\xbcgo'.decode('utf-8'),
                       lastname='Boss'))

        actor = Actor.lookup('hugo.boss')

        self.assertEqual(u'Boss H\xfcgo (hugo.boss)', actor.get_label())
        self.assertTrue(
            actor.get_profile_url().endswith('@@user-details/hugo.boss'))

        self.assertEqual(
            u'<a href="http://nohost/plone/@@user-details/hugo.boss">Boss H\xfcgo (hugo.boss)</a>',
            actor.get_link())


class TestActorCorresponding(FunctionalTestCase):

    def setUp(self):
        super(TestActorCorresponding, self).setUp()
        self.user, self.org_unit, self.admin_unit = create(
            Builder('fixture').with_all_unit_setup())
        self.hugo = create(Builder('ogds_user')
                           .id('hugo.boss')
                           .having(firstname='H\xc3\xbcgo'.decode('utf-8'),
                                   lastname='Boss'))

    @unittest.skip('something went wrong with the sqlalchemy session')
    def test_user_corresponds_to_current_user(self):
        actor = Actor.lookup(TEST_USER_ID)

        self.assertTrue(actor.corresponds_to(self.user))
        self.assertFalse(actor.corresponds_to(self.hugo))

    @unittest.skip('something went wrong with the sqlalchemy session')
    def test_inbox_corresponds_to_all_inbox_assigned_users(self):
        actor = Actor.lookup('inbox:client1')

        self.assertTrue(actor.corresponds_to(self.user))
        self.assertFalse(actor.corresponds_to(self.hugo))
