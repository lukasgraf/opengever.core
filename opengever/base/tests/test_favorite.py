from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browsing
from opengever.base.model import create_session
from opengever.base.model.favorite import Favorite
from opengever.base.oguid import Oguid
from opengever.testing import IntegrationTestCase
from opengever.trash.trash import Trasher
from plone import api
from sqlalchemy.exc import IntegrityError


class TestFavoriteModel(IntegrationTestCase):

    def test_add_favorite(self):
        favorite = Favorite(
            oguid=Oguid.parse('fd:123'),
            userid=self.regular_user.getId(),
            title=u'Testposition 1',
            position=2,
            portal_type='opengever.repositoryfolder.repositoryfolder',
            icon_class='contenttype-opengever-repository-repositoryfolder',
            plone_uid='127bad76e535451493bb5172c28eb38d')

        create_session().add(favorite)

        self.assertEqual(1, Favorite.query.count())
        self.assertEqual(u'Testposition 1', Favorite.query.one().title)

    def test_unique_constraint(self):
        data = {
            'oguid': Oguid.parse('fd:123'),
            'userid': self.regular_user.getId(),
            'title': u'Testposition 1',
            'position': 2,
            'portal_type': 'opengever.repositoryfolder.repositoryfolder',
            'icon_class': 'contenttype-opengever-repository-repositoryfolder',
            'plone_uid': '127bad76e535451493bb5172c28eb38d'}

        session = create_session()
        session.add(Favorite(**data))

        with self.assertRaises(IntegrityError):
            session.add(Favorite(**data))
            session.flush()

    def test_is_marked_as_favorite(self):
        self.login(self.regular_user)

        create(Builder('favorite')
               .for_object(self.document)
               .for_user(self.regular_user))

        create(Builder('favorite')
               .for_object(self.dossier)
               .for_user(self.dossier_responsible))

        self.assertFalse(
            Favorite.query.is_marked_as_favorite(self.document, self.dossier_responsible))
        self.assertTrue(
            Favorite.query.is_marked_as_favorite(self.document, self.regular_user))
        self.assertFalse(
            Favorite.query.is_marked_as_favorite(self.dossier, self.regular_user))


class TestHandlers(IntegrationTestCase):

    def test_all_favorites_are_deleted_when_removing_object(self):
        self.login(self.manager)

        create(Builder('favorite')
               .for_object(self.dossier)
               .for_user(self.administrator))

        create(Builder('favorite')
               .for_object(self.empty_dossier)
               .for_user(self.dossier_responsible))

        self.assertEquals(2, Favorite.query.count())

        api.content.delete(obj=self.empty_dossier)

        self.assertEquals(1, Favorite.query.count())

    def test_all_favorites_are_deleted_when_moving_a_document_to_trash(self):
        self.login(self.regular_user)

        create(Builder('favorite')
               .for_object(self.dossier)
               .for_user(self.administrator))

        create(Builder('favorite')
               .for_object(self.document)
               .for_user(self.dossier_responsible))

        self.assertEquals(2, Favorite.query.count())

        Trasher(self.document).trash()

        self.assertEquals(1, Favorite.query.count())

    @browsing
    def test_titled_of_favorites_get_updated(self, browser):
        self.login(self.regular_user, browser=browser)

        fav1 = create(Builder('favorite')
                      .for_object(self.dossier)
                      .for_user(self.administrator)
                      .having(is_title_personalized=True,
                              title='GEVER Weeklies'))

        fav2 = create(Builder('favorite')
                      .for_object(self.dossier)
                      .for_user(self.regular_user))

        self.assertEquals('GEVER Weeklies', fav1.title)
        self.assertEquals(
            u'Vertr\xe4ge mit der kantonalen Finanzverwaltung', fav2.title)

        browser.open(self.dossier, view='edit')
        browser.fill({u'Title': u'Anfragen 2018'})
        browser.click_on('Save')

        self.assertEquals('GEVER Weeklies',
                          Favorite.query.get(fav1.favorite_id).title)
        self.assertEquals(u'Anfragen 2018', Favorite.query.get(fav2.favorite_id).title)
