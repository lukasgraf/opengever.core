from collections import OrderedDict
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.interfaces import ISectionBlueprint
from opengever.base.interfaces import IReferenceNumberFormatter
from opengever.base.interfaces import IReferenceNumberSettings
from opengever.bundle.sections.bundlesource import BUNDLE_KEY
from plone import api
from zope.annotation import IAnnotations
from zope.component import queryAdapter
from zope.interface import classProvides
from zope.interface import implements
import logging


TYPES_WITHOUT_REFERENCE_NUMBER = [
    'opengever.task.task',
    'opengever.meeting.proposal',
    'opengever.meeting.submittedproposal']

log = logging.getLogger('opengever.bundle.resolveguid')
log.setLevel(logging.INFO)


class MissingGuid(Exception):
    pass


class DuplicateGuid(Exception):
    pass


class MissingParent(Exception):
    pass


class ReferenceNumberNotFound(Exception):
    pass


class ResolveGUIDSection(object):
    """Resolve and validate GUIDs.

    Each item must define a globally unique identifier (GUID) wich is used as
    identifier while importing an oggbundle. The format of this id can be
    chosen freely.

    Yield items in an order that guarantees that parents are always positioned
    before their children. This is achieved by building a temporary tree, then
    re-yielding the children in pre-order.

    This section also validates that:
        - each item has a guid
        - each guid is unique
        - parent pointers are valid, should they exist

    """

    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.transmogrifier = transmogrifier
        self.bundle = IAnnotations(transmogrifier)[BUNDLE_KEY]

        self.bundle.item_by_guid = OrderedDict()
        self.bundle.path_by_reference_number = OrderedDict()

        # Table of formatted refnums that exist in Plone
        self.bundle.existing_refnums = ()

        self.formatter = None

        self.catalog = api.portal.get_tool('portal_catalog')

    def __iter__(self):
        self.register_items_by_guid()
        roots = self.build_tree()
        for node in self.visit_in_pre_order(
                roots, level=1, previous_type='Portal'):
            yield node

    def get_formatter(self):
        if not self.formatter:
            active_formatter = api.portal.get_registry_record(
                name='formatter', interface=IReferenceNumberSettings)
            self.formatter = queryAdapter(
                api.portal.get(), IReferenceNumberFormatter,
                name=active_formatter)

        return self.formatter

    def get_existing_refnums(self):
        index = self.catalog._catalog.indexes['reference']
        return tuple(index.uniqueValues())

    def register_items_by_guid(self):
        """Register all items by their guid."""
        # Collect existing reference numbers from catalog index
        self.bundle.existing_refnums = self.get_existing_refnums()

        # Keep track of all reference numbers referred to in bundle items
        used_ref_numbers = []

        for item in self.previous:
            if 'guid' not in item:
                raise MissingGuid(item)

            guid = item['guid']
            if guid in self.bundle.item_by_guid:
                raise DuplicateGuid(guid)

            self.bundle.item_by_guid[guid] = item

            if 'parent_reference' in item:
                parent_refnum = self.get_formatter().list_to_string(
                    item['parent_reference'])
                item['_formatted_parent_refnum'] = parent_refnum
                used_ref_numbers.append(parent_refnum)

        log.info('Start building reference mapping')
        self.bundle.path_by_reference_number = self.build_reference_mapping(
            used_ref_numbers)
        log.info('Reference mapping built.')

        # Verify that all parent containers referenced by refnum exist in Plone
        for formatted_refnum in used_ref_numbers:
            if formatted_refnum not in self.bundle.existing_refnums:
                # Reference number of referenced parent not found in catalog
                raise ReferenceNumberNotFound(
                    "Couldn't find container with reference number %s "
                    "(referenced as parent by item by GUID %s )" % (
                        formatted_refnum, guid))

    def get_relative_path(self, brain):
        """Returns the path relative to the plone site for the given brain.
        """
        return '/'.join(brain.getPath().split('/')[2:])

    def build_reference_mapping(self, reference_numbers):
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.unrestrictedSearchResults(reference=reference_numbers)
        return {
            brain.reference: self.get_relative_path(brain) for brain in brains
            if brain.portal_type not in TYPES_WITHOUT_REFERENCE_NUMBER}

    def build_tree(self):
        """Build a tree from the flat list of items.

        Register all items with their parents.
        """
        roots = []
        for item in self.bundle.item_by_guid.values():
            parent_guid = item.get('parent_guid', None)
            if parent_guid:
                parent = self.bundle.item_by_guid.get(parent_guid)
                if not parent:
                    msg = "%r (referenced by GUID %r)" % (
                        parent_guid, item['guid'])
                    raise MissingParent(msg)
                children = parent.setdefault('_children', [])
                children.append(item)
            else:
                roots.append(item)
        return roots

    def visit_in_pre_order(self, items, level, previous_type):
        """Visit list of items depth first, always yield parent before its
        children.

        In addition, keep track of the nesting depth of objects of the *same
        type* - this is used for validation in a later section.
        """
        for item in items:
            type_ = item.get('_type')

            # Type of nested folderish items changed - reset nesting depth
            if previous_type != type_:
                level = 1

            item['_nesting_depth'] = level
            children = item.pop('_children', [])
            yield item

            for child in self.visit_in_pre_order(
                    children, level + 1, type_):
                yield child
