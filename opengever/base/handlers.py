from ftw.upgrade.helpers import update_security_for
from opengever.base.model import create_session
from opengever.base.model.favorite import Favorite
from opengever.base.oguid import Oguid
from opengever.base.touched import ObjectTouchedEvent
from opengever.base.touched import should_track_touches
from plone import api
from plone.app.workflow.interfaces import ILocalrolesModifiedEvent
from Products.CMFCore.CMFCatalogAware import CatalogAware
from Products.CMFPlone.interfaces import IPloneSiteRoot
from sqlalchemy import and_
from zope.container.interfaces import IContainerModifiedEvent
from zope.event import notify
from zope.lifecycleevent import IObjectRemovedEvent
from zope.lifecycleevent import ObjectAddedEvent
from zope.sqlalchemy.datamanager import mark_changed


def object_moved_or_added(context, event):
    if isinstance(event, ObjectAddedEvent):
        # Don't consider moving or removing an object a "touch". Mass-moves
        # would immediately fill up the touched log, and removals should not
        # be tracked anyway.
        if should_track_touches(context):
            notify(ObjectTouchedEvent(context))

    if IObjectRemovedEvent.providedBy(event):
        return

    # Update object security after moving or copying.
    # Specifically, this is needed for the case where an object is moved out
    # of a location where a Placeful Workflow Policy applies to a location
    # where it doesn't.
    #
    #  Plone then no longer provides the placeful workflow for that object,
    # but doesn't automatically update the object's security.
    #
    # We use ftw.upgrade's update_security_for() here to correctly
    # recalculate security, but do the reindexing ourselves because otherwise
    # Plone will do it recursively (unnecessarily so).
    changed = update_security_for(context, reindex_security=False)
    if changed:
        catalog = api.portal.get_tool('portal_catalog')
        catalog.reindexObject(context, idxs=CatalogAware._cmf_security_indexes,
                              update_metadata=0)


def remove_favorites(context, event):
    """Event handler which removes all existing favorites for the
    current context.
    """

    # Skip plone site removals. Unfortunately no deletion-order seems to be
    # guaranteed, when removing the plone site, so it might happen that the
    # intid utility is removed before removing content.
    if IPloneSiteRoot.providedBy(event.object):
        return

    oguid = Oguid.for_object(context)

    stmt = Favorite.__table__.delete().where(Favorite.oguid == oguid)
    create_session().execute(stmt)


def is_title_changed(descriptions):
    for desc in descriptions:
        for attr in desc.attributes:
            if attr in ['IOpenGeverBase.title', 'title']:
                return True
    return False


def object_modified(context, event):
    update_favorites_title(context, event)

    if should_track_touches(context):
        notify(ObjectTouchedEvent(context))


def update_favorites_title(context, event):
    """Event handler which updates the titles of all existing favorites for the
    current context, unless the title is personalized.
    """
    if IContainerModifiedEvent.providedBy(event):
        return

    if ILocalrolesModifiedEvent.providedBy(event):
        return

    if is_title_changed(event.descriptions):
        query = Favorite.query.filter(
            and_(Favorite.oguid == Oguid.for_object(context),
                 Favorite.is_title_personalized == False))  # noqa
        query.update({'title': context.title})

        mark_changed(create_session())
