from datetime import datetime
from ftw.builder import Builder
from ftw.builder import create
from ftw.builder import ticking_creator
from ftw.tabbedview.interfaces import ITabbedView
from ftw.testbrowser import browsing
from ftw.testing import freeze
from opengever.bumblebee import BUMBLEBEE_VIEW_COOKIE_NAME
from opengever.core.testing import OPENGEVER_FUNCTIONAL_BUMBLEBEE_LAYER
from opengever.tabbedview.browser.bumblebee_gallery import BumblebeeGalleryMixin
from opengever.tabbedview.browser.tabs import BaseTabProxy
from opengever.tabbedview.interfaces import ITabbedViewProxy
from opengever.testing import FunctionalTestCase
from opengever.testing import obj2paths
from plone import api
from zExceptions import NotFound
from zope.component import getMultiAdapter
from zope.interface.verify import verifyClass
import transaction


def set_cookie(request, value):
    # We cannot use set_preferred_listing_view from opengever.bumblebee
    # because it wont set the cookie properly in tests.
    #
    # Because that, we set the cookie value directly into the request
    request.cookies[BUMBLEBEE_VIEW_COOKIE_NAME] = value


class MockProxyTabView(BaseTabProxy):
    __name__ = 'tabbedview_view-mocktab-proxy'


class TestBaseTabProxyWithDeactivatedFeature(FunctionalTestCase):

    def test_preferred_view_name_returns_always_list_view(self):
        proxy_view = MockProxyTabView(self.portal, self.request)

        set_cookie(self.request, 'gallery')

        self.assertEqual(
            'tabbedview_view-mocktab', proxy_view.preferred_view_name)

        set_cookie(self.request, 'list')

        self.assertEqual(
            'tabbedview_view-mocktab', proxy_view.preferred_view_name)


class TestBaseTabProxyWithActivatedFeature(FunctionalTestCase):

    layer = OPENGEVER_FUNCTIONAL_BUMBLEBEE_LAYER

    def test_verify_class(self):
        verifyClass(ITabbedViewProxy, BaseTabProxy)

    def test_name_without_postfix_extract_postfix_from_view_name(self):
        proxy_view = MockProxyTabView(self.portal, self.request)

        self.assertEqual(
            'tabbedview_view-mocktab', proxy_view.name_without_postfix)

    def test_list_view_name_returns_proxy_view_name_without_postfix(self):
        proxy_view = MockProxyTabView(self.portal, self.request)

        self.assertEqual(
            'tabbedview_view-mocktab', proxy_view.list_view_name)

    def test_gallery_view_name_returns_list_view_name_with_gallery_postfix(self):
        proxy_view = MockProxyTabView(self.portal, self.request)

        self.assertEqual(
            'tabbedview_view-mocktab-gallery', proxy_view.gallery_view_name)

    def test_preferred_view_name_returns_last_used_view_name(self):
        proxy_view = MockProxyTabView(self.portal, self.request)

        set_cookie(self.request, 'gallery')

        self.assertEqual(
            'tabbedview_view-mocktab-gallery', proxy_view.preferred_view_name)

        set_cookie(self.request, 'list')

        self.assertEqual(
            'tabbedview_view-mocktab', proxy_view.preferred_view_name)


class TestBumblebeeGalleryMixin(FunctionalTestCase):

    @browsing
    def test_calling_mixin_raise_404_if_feature_is_deactivated(self, browser):
        with self.assertRaises(NotFound):
            BumblebeeGalleryMixin()(self.portal, self.request)


class TestBumblebeeGalleryMixinListViewName(FunctionalTestCase):

    layer = OPENGEVER_FUNCTIONAL_BUMBLEBEE_LAYER

    def test_list_view_name_returns_view_name_for_documents_listing(self):
        dossier = create(Builder('dossier'))

        viewname = "tabbedview_view-documents-gallery"
        view = getMultiAdapter(
            (dossier, self.request), name=viewname)

        self.assertEqual('documents', view.list_view_name)

        viewname = "tabbedview_view-mydocuments-gallery"
        view = getMultiAdapter(
            (self.portal, self.request), name=viewname)

        self.assertEqual('mydocuments', view.list_view_name)


class TestBumblebeeGalleryMixinGetFetchUrl(FunctionalTestCase):

    layer = OPENGEVER_FUNCTIONAL_BUMBLEBEE_LAYER

    def test_get_fetch_url_returns_the_url_to_fetch_new_items(self):
        dossier = create(Builder('dossier'))

        viewname = "tabbedview_view-documents-gallery"
        view = getMultiAdapter(
            (dossier, self.request), name=viewname)

        self.assertEqual(
            'http://nohost/plone/dossier-1/tabbedview_view-documents-gallery/fetch',
            view.get_fetch_url())

        viewname = "tabbedview_view-mydocuments-gallery"
        view = getMultiAdapter(
            (dossier, self.request), name=viewname)

        self.assertEqual(
            'http://nohost/plone/dossier-1/tabbedview_view-mydocuments-gallery/fetch',
            view.get_fetch_url())


class TestBumblebeeGalleryMixinGetBrains(FunctionalTestCase):

    layer = OPENGEVER_FUNCTIONAL_BUMBLEBEE_LAYER

    def test_returns_brains_depending_on_tablesource_query(self):
        dossier = create(Builder('dossier'))
        other_dossier = create(Builder('dossier'))
        view = getMultiAdapter(
            (dossier, self.request), name="tabbedview_view-documents-gallery")

        with freeze(datetime(2010, 1, 1)) as clock:
            old_document = create(Builder('document').within(dossier))
            clock.forward(days=1)

            new_document = create(Builder('document').within(dossier))
            clock.forward(days=1)

            create(Builder('document').within(other_dossier))

            brains = view.get_brains()
            self.assertEqual([new_document, old_document],
                             [brain.getObject() for brain in brains])

    def test_brain_listing_is_cached_per_request(self):
        dossier = create(Builder('dossier'))
        view = getMultiAdapter(
            (dossier, self.request), name="tabbedview_view-documents-gallery")

        create(Builder('document').within(dossier))
        self.assertEqual(1, len(view.get_brains()))

        create(Builder('document').within(dossier))
        self.assertEqual(
            1, len(view.get_brains()),
            "Should still be 1 because the catalog cache")

    @browsing
    def test_returns_only_ibumblebeeable_objects(self, browser):
        dossier = create(Builder('dossier'))

        # IBumblebeeable document
        create(Builder('document').within(dossier))

        # Remove IBumblebeeable behavior
        ibumblebeeable_behavior = 'ftw.bumblebee.interfaces.IBumblebeeable'
        ttool = api.portal.get_tool('portal_types')
        doc_fti = ttool.get('opengever.document.document')
        doc_fti.behaviors = [behavior for behavior in doc_fti.behaviors
                             if behavior != ibumblebeeable_behavior]

        transaction.commit()

        # Not an IBumblebeeable document
        create(Builder('document').within(dossier))

        view = getMultiAdapter(
            (dossier, self.request), name="tabbedview_view-documents-gallery")

        self.assertEqual(
            1, len(view.get_brains()),
            "Should only display one document because the second "
            "is not and IBumblebeeable object")

    @browsing
    def test_respects_searchable_text_in_request(self, browser):
        dossier = create(Builder('dossier'))
        view = getMultiAdapter(
            (dossier, self.request), name="tabbedview_view-documents-gallery")

        document = create(Builder('document')
                          .within(dossier)
                          .titled("James Bond"))

        create(Builder('document')
               .within(dossier)
               .titled("Chuck Norris"))

        view.request['searchable_text'] = "James"
        brains = view.get_brains()

        self.assertEqual([document, ], [brain.getObject() for brain in brains])


class TestBumblebeeGalleryMixinFetch(FunctionalTestCase):

    @browsing
    def test_returns_new_items_as_html(self, browser):
        dossier = create(Builder('dossier'))

        create(Builder('document').within(dossier))
        create(Builder('document').within(dossier))
        create(Builder('document').within(dossier))

        view = getMultiAdapter(
            (dossier, self.request), name="tabbedview_view-documents-gallery")

        browser.open_html(view.fetch())

        self.assertEqual(3, len(browser.css('.imageContainer')))

    def test_returns_empty_string_if_no_items_are_available(self):
        dossier = create(Builder('dossier'))

        view = getMultiAdapter(
            (dossier, self.request), name="tabbedview_view-documents-gallery")

        self.assertEqual('', view.fetch())

    def test_returns_empty_string_if_pointer_does_not_point_to_any_object(self):
        dossier = create(Builder('dossier'))

        create(Builder('document').within(dossier))

        self.request.set('documentPointer', 20)

        view = getMultiAdapter(
            (dossier, self.request), name="tabbedview_view-documents-gallery")

        self.assertEqual('', view.fetch())


class TestBumblebeeGalleryViewChooserWithoutFeature(FunctionalTestCase):

    @browsing
    def test_do_not_show_viewchooser_on_my_documents_tab(self, browser):
        browser.login().open(self.portal, view='tabbedview_view-mydocuments')
        self.assertEqual(0, len(browser.css('.ViewChooser')))

    @browsing
    def test_do_not_show_viewchooser_on_documents_tab(self, browser):
        browser.login().open(self.portal, view='tabbedview_view-mydocuments')
        self.assertEqual(0, len(browser.css('.ViewChooser')))


class TestBumblebeeGalleryViewChooser(FunctionalTestCase):

    layer = OPENGEVER_FUNCTIONAL_BUMBLEBEE_LAYER

    @browsing
    def test_show_viewchooser_if_feature_is_activated_on_my_documents_tab(self, browser):
        browser.login().open(self.portal, view='tabbedview_view-mydocuments')
        self.assertEqual(1, len(browser.css('.ViewChooser')))

    @browsing
    def test_show_viewchooser_if_feature_is_activated_on_documents_tab(self, browser):
        browser.login().open(self.portal, view='tabbedview_view-mydocuments')
        self.assertEqual(1, len(browser.css('.ViewChooser')))


class TestBumblebeeGalleryView(FunctionalTestCase):

    layer = OPENGEVER_FUNCTIONAL_BUMBLEBEE_LAYER

    @browsing
    def test_show_image_container_for_each_document(self, browser):
        dossier = create(Builder('dossier'))

        create(Builder('document').within(dossier))
        create(Builder('document').within(dossier))

        browser.login().visit(dossier, view="tabbedview_view-documents-gallery")

        self.assertEqual(2, len(browser.css('.imageContainer')))

    @browsing
    def test_show_fallback_message_if_no_documents_are_available(self, browser):
        dossier = create(Builder('dossier'))

        browser.login().visit(dossier, view="tabbedview_view-documents-gallery")

        self.assertEqual(0, len(browser.css('.imageContainer')))
        self.assertEqual("No contents", browser.css('.no_content').first.text)

    @browsing
    def test_link_previews_to_bumblebee_overlay_listing(self, browser):
        dossier = create(Builder('dossier'))

        create(Builder('document').within(dossier))

        browser.login().visit(dossier, view="tabbedview_view-documents-gallery")

        self.assertEqual(
            'http://nohost/plone/dossier-1/document-1/@@bumblebee-overlay-listing',
            browser.css('.imageContainer').first.get('data-showroom-target'))


class TestDocumentsGalleryFetch(FunctionalTestCase):

    @browsing
    def test_fetching_new_items_returns_html_with_items(self, browser):
        dossier = create(Builder('dossier'))

        create(Builder('document').within(dossier))
        create(Builder('document').within(dossier))
        create(Builder('document').within(dossier))

        browser.login().visit(dossier, view="tabbedview_view-documents-gallery/fetch")

        self.assertEqual(
            3, len(browser.css('.imageContainer')))


class TestMyDocumentsGalleryFetch(FunctionalTestCase):

    @browsing
    def test_fetching_new_items_returns_html_with_items(self, browser):
        dossier = create(Builder('dossier'))

        create(Builder('document').within(dossier))
        create(Builder('document').within(dossier))
        create(Builder('document').within(dossier))

        browser.login().visit(dossier, view="tabbedview_view-mydocuments-gallery/fetch")

        self.assertEqual(
            3, len(browser.css('.imageContainer')))


class TestProxyViewsWithDeactivatedFeature(FunctionalTestCase):

    @browsing
    def test_do_not_set_cookie_on_documents_tab(self, browser):
        dossier = create(Builder('dossier'))

        browser.login().visit(dossier, view="tabbedview_view-documents-proxy")
        self.assertIsNone(browser.cookies.get(BUMBLEBEE_VIEW_COOKIE_NAME))

    @browsing
    def test_do_not_set_cookie_on_mydocuments_tab(self, browser):
        browser.login().visit(view="tabbedview_view-mydocuments-proxy")
        self.assertIsNone(browser.cookies.get(BUMBLEBEE_VIEW_COOKIE_NAME))

    @browsing
    def test_do_not_set_cookie_on_trash_tab(self, browser):
        dossier = create(Builder('dossier'))

        browser.login().visit(dossier, view="tabbedview_view-trash-proxy")
        self.assertIsNone(browser.cookies.get(BUMBLEBEE_VIEW_COOKIE_NAME))

    @browsing
    def test_do_not_set_cookie_on_related_documents_tab(self, browser):
        dossier = create(Builder('dossier'))
        task = create(Builder('task').within(dossier))

        browser.login().visit(task, view="tabbedview_view-relateddocuments-proxy")
        self.assertIsNone(browser.cookies.get(BUMBLEBEE_VIEW_COOKIE_NAME))


class TestProxyViewsWithActivatedFeature(FunctionalTestCase):

    layer = OPENGEVER_FUNCTIONAL_BUMBLEBEE_LAYER

    @browsing
    def test_documents_proxy_tab(self, browser):
        dossier = create(Builder('dossier'))

        browser.login().visit(dossier, view="tabbedview_view-documents-proxy")

        self.assertEqual(
            'List',
            browser.css('.ViewChooser .active').first.text)

        # Set cookie for gallery-view
        browser.login().visit(dossier, view="tabbedview_view-documents-gallery")

        browser.login().visit(dossier, view="tabbedview_view-documents-proxy")

        self.assertEqual(
            'Gallery',
            browser.css('.ViewChooser .active').first.text)

    @browsing
    def test_dossiertemplates_documents_proxy_tab(self, browser):
        dossiertemplate = create(Builder('dossiertemplate')
                                 .titled(u'My Dossiertemplate'))

        browser.login().visit(dossiertemplate, view="tabbedview_view-documents-proxy")

        self.assertEqual(
            'List',
            browser.css('.ViewChooser .active').first.text)

        # Set cookie for gallery-view
        browser.login().visit(dossiertemplate, view="tabbedview_view-documents-gallery")

        browser.login().visit(dossiertemplate, view="tabbedview_view-documents-proxy")

        self.assertEqual(
            'Gallery',
            browser.css('.ViewChooser .active').first.text)

    @browsing
    def test_mydocuments_proxy_tab(self, browser):
        browser.login().visit(
            self.portal, view="tabbedview_view-mydocuments-proxy")

        self.assertEqual(
            'List',
            browser.css('.ViewChooser .active').first.text)

        # Set cookie for gallery-view
        browser.login().visit(
            self.portal, view="tabbedview_view-mydocuments-gallery")

        browser.login().visit(view="tabbedview_view-mydocuments-proxy")

        self.assertEqual(
            'Gallery',
            browser.css('.ViewChooser .active').first.text)

    @browsing
    def test_trash_proxy_tab(self, browser):
        dossier = create(Builder('dossier'))

        browser.login().visit(dossier, view="tabbedview_view-trash-proxy")

        self.assertEqual(
            'List',
            browser.css('.ViewChooser .active').first.text)

        # Set cookie for gallery-view
        browser.login().visit(dossier, view="tabbedview_view-trash-gallery")

        browser.login().visit(dossier, view="tabbedview_view-trash-proxy")

        self.assertEqual(
            'Gallery',
            browser.css('.ViewChooser .active').first.text)

    @browsing
    def test_relateddocuments_proxy_tab(self, browser):
        dossier = create(Builder('dossier'))
        task = create(Builder('task').within(dossier))

        browser.login().visit(task, view="tabbedview_view-relateddocuments-proxy")

        self.assertEqual(
            'List',
            browser.css('.ViewChooser .active').first.text)

        # Set cookie for gallery-view
        browser.login().visit(task, view="tabbedview_view-relateddocuments-gallery")

        browser.login().visit(task, view="tabbedview_view-relateddocuments-proxy")

        self.assertEqual(
            'Gallery',
            browser.css('.ViewChooser .active').first.text)

    @browsing
    def test_select_all_use_preferred_view_content_query(self, browser):
        dossier = create(Builder('dossier'))

        document_a = create(Builder('document').within(dossier))
        create(Builder('document'))

        data = {'view_name': 'documents-proxy',
                'initialize': 0,
                'selected_count': 0}
        browser.login().open(dossier, data, view='tabbed_view/select_all')

        self.assertEqual(
            obj2paths([document_a]),
            [input.get('value') for input in browser.css('input')])
