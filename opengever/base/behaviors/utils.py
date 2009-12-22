
from Acquisition import aq_inner, aq_parent
import zope.schema.vocabulary

from Products.CMFCore.interfaces import ISiteRoot
from plone.app.dexterity.behaviors.metadata import MetadataBase

def create_restricted_vocabulary(field, options, message_factory=None):
    """
    Creates a restricted vocabulary.
    Expects a options list which looks as follows:
    options = (
    (0,     u'none'),
    (1,     u'raw_option_one'),
    (1,     u'raw_option_two'),
    (2,     u'detailed_option_one'),
    (2,     u'detailed_option_two'),
    )

    Use the string as internationalization message-id.

    What it does in the example:
    if the parent object has a "raw" option set, then only detailed
    options or the selected raw option are allowed to be selected.
    """
    class GeneratedVocabulary(object):

        @property
        def option_level_mapping(self):
            option_level_mapping = [list(a) for a in self.options[:]]
            option_level_mapping = dict([a for a in option_level_mapping
                                         if not a.reverse()])
            return option_level_mapping

        @property
        def option_names(self):
            return [a[1] for a in self.options]

        @property
        def options(self):
            if callable(self._options):
                return self._options()
            else:
                return self._options

        def __call__(self, context):
            self.context = context
            # decide, whats allowed
            allowed_option_names = []
            acquisition_value = self._get_acquisiton_value()
            if acquisition_value and acquisition_value in self.option_names:
                allowed_option_names.append(acquisition_value)
                allowed_level = self.option_level_mapping[acquisition_value] + 1
                for level, name in self.options:
                    if level >= allowed_level:
                        allowed_option_names.append(name)
            else:
                allowed_option_names = self.option_names
            # make the terms
            terms = []
            for name in allowed_option_names:
                title = name
                if message_factory:
                    title = self._(name)
                terms.append(zope.schema.vocabulary.SimpleTerm(name, title=title))
            return zope.schema.vocabulary.SimpleVocabulary(terms)

        def _get_acquisiton_value(self):
            context = self.context
            if isinstance(context, MetadataBase):
                # we do not test the factory, it is not acquisition wrapped and
                # we cant get the request...
                return None
            request = self.context.REQUEST
            if '++add++' in request.get('PATH_TRANSLATED', object()):
                # object is not yet existing, context is container
                obj = context
            else:
                # object is existing, container is parent of context
                obj = context.aq_inner.aq_parent
            while not ISiteRoot.providedBy(obj):
                try:
                    return self.field.get(obj)
                except AttributeError:
                    try:
                        interface_ = self.field.interface
                    except AttributeError:
                        pass
                    else:
                        try:
                            adpt = interface_(obj)
                        except TypeError: # could not adapt
                            pass
                        else:
                            return self.field.get(adpt)
                obj = obj.aq_inner.aq_parent
            return self.field.default

    GeneratedVocabulary.field = field
    GeneratedVocabulary._options = options
    GeneratedVocabulary._ = message_factory
    return GeneratedVocabulary


def set_default_with_acquisition(field, default):
    """
    Sets a default value generator which uses the value
    from the parent object, if existing, otherwise it uses
    the given default value.
    """
    field._acquisition_default = default
    def default_value_generator(data):
        obj = data.context
        # try to get it from context or a parent
        while not ISiteRoot.providedBy(obj):
            try:
                return data.field.get(obj)
            except AttributeError:
                try:
                    interface_ = data.field.interface
                except AttributeError:
                    pass
                else:
                    try:
                        adpt = interface_(obj)
                    except TypeError: # could not adapt
                        pass
                    else:
                        return data.field.get(adpt)
            obj = aq_parent(aq_inner(obj))
        # otherwise use default value
        return field._acquisition_default
    return default_value_generator

