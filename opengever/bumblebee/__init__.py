from ftw.bumblebee.utils import get_representation_url_by_brain as representation_url_by_brain
from ftw.bumblebee.utils import get_representation_url_by_object as representation_url_by_object
from opengever.bumblebee.interfaces import IGeverBumblebeeSettings
from plone import api


def get_preserved_as_paper_placeholder_image_url():
    return "{}{}".format(
        api.portal.get().absolute_url(),
        "/++resource++opengever.base/images/preserved_as_paper.png")


def is_bumblebee_feature_enabled():
    return api.portal.get_registry_record(
        'is_feature_enabled', interface=IGeverBumblebeeSettings)


def get_representation_url_by_object(format_name, obj):
    """Returns the bumblebee representation url of the object.

    Bumblebee will return the representation if the obj has a checksum.
    The checksum is only available if the obj has an attached document.

    If no checksum is available, the representation_url will be none.

    That means, our obj is only preserved as paper and we have to return
    a special placeholder image for these documents
    """
    return representation_url_by_object(format_name, obj) or \
        get_preserved_as_paper_placeholder_image_url()


def get_representation_url_by_brain(format_name, brain):
    """Returns the bumblebee representation url of the brain.

    Bumblebee will return the representation if the brain has a checksum.
    The checksum is only available if the brain has an attached document.

    If no checksum is available, the representation_url will be none.

    That means, our brain is only preserved as paper and we have to return
    a special placeholder image for these documents
    """
    return representation_url_by_brain(format_name, brain) or \
        get_preserved_as_paper_placeholder_image_url()
