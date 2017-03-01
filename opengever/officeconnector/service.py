from opengever.document.document import IDocumentSchema
from opengever.officeconnector.helpers import is_officeconnector_attach_feature_enabled  # noqa
from opengever.officeconnector.helpers import is_officeconnector_checkout_feature_enabled  # noqa
from plone import api
from plone.protect import createToken
from plone.rest import Service
from Products.CMFCore.utils import getToolByName
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin  # noqa
from zExceptions import Forbidden
from zExceptions import NotFound
from zope.interface import implements
from zope.publisher.interfaces import IPublishTraverse

import json


class OfficeConnectorURL(Service):
    """Create oc:<JWT> URLs for javascript to fetch and pass to the OS."""

    def create_officeconnector_url(self, payload):
        # Feature used wrong - an action is always required
        if 'action' not in payload:
            raise NotFound

        # Feature enabled for the wrong content type
        if not IDocumentSchema.providedBy(self.context):
            raise NotFound

        if not self.context.file:
            raise NotFound
        plugin = None
        acl_users = getToolByName(self.context, "acl_users")
        plugins = acl_users._getOb('plugins')
        authenticators = plugins.listPlugins(IAuthenticationPlugin)

        # Assumes there is only one JWT auth plugin present in the acl_users
        # which manages the user/session in question.
        #
        # This will work as long as the plugin this finds uses the same secret
        # as whatever it ends up authenticating against - this is in all
        # likelihood the Plone site keyring.
        for id_, authenticator in authenticators:
            if authenticator.meta_type == "JWT Authentication Plugin":
                plugin = authenticator
                break

        if not plugin:
            raise Forbidden

        # Create a JWT for OfficeConnector - contents:
        # action - tells OfficeConnector which code path to take
        # url - tells OfficeConnector where from to fetch further instructions
        payload['url'] = '/'.join([
            api.portal.get().absolute_url(),
            'oc_' + payload['action'],
            api.content.get_uuid(self.context),
            ])
        user_id = api.user.get_current().getId()
        token = plugin.create_token(user_id, data=payload)

        # https://blogs.msdn.microsoft.com/ieinternals/2014/08/13/url-length-limits/
        # IE11 only allows up to 507 characters for Application Protocols.
        #
        # This is eaten into by both the protocol identifier and the payload.
        #
        # In testing we've discovered for this to be a bit fuzzy and gotten
        # arbitrary and inconsistent results of 506..509.
        #
        # For operational safety we've set the total url + separator + payload
        # limit at 500 characters.
        url = 'oc:' + token
        self.request.response.setHeader('Content-type', 'application/json')
        if len(url) <= 500:
            return json.dumps(dict(url=url))
        else:
            self.request.response.setStatus(500)
            return json.dumps(dict(error=dict(
                type='Generated URL too long',
                message='The URL is too long for IE11',
            )))


class OfficeConnectorAttachURL(OfficeConnectorURL):
    """Create oc:<JWT> URLs for javascript to fetch and pass to the OS.

    Instruct where to fetch an OfficeConnector 'attach' action payload for this
    document.
    """

    def render(self):
        # Feature disabled or used wrong
        if not is_officeconnector_attach_feature_enabled():
            raise NotFound
        payload = {'action': 'attach'}
        return self.create_officeconnector_url(payload)


class OfficeConnectorCheckoutURL(OfficeConnectorURL):
    """Create oc:<JWT> URLs for javascript to fetch and pass to the OS.

    Instruct where to fetch an OfficeConnector 'checkout' action payload for
    this document.
    """

    def render(self):
        # Feature disabled or used wrong
        if not is_officeconnector_checkout_feature_enabled():
            raise NotFound

        payload = {'action': 'checkout'}

        return self.create_officeconnector_url(payload)


class OfficeConnectorPayload(Service):
    """Issue JSON instruction payloads for OfficeConnector."""

    implements(IPublishTraverse)

    def __init__(self, context, request):
        super(OfficeConnectorPayload, self).__init__(context, request)
        self.uuid = None
        self.document = None

    def publishTraverse(self, request, name):
        # This gets called once per path segment
        if self.uuid is None:
            self.uuid = name
        else:
            # Block traversing further path segments
            raise NotFound(self, name, request)
        return self

    def get_base_payload(self):
        # Do not 404 if we do not have a normal user
        if api.user.is_anonymous():
            raise Forbidden
        self.document = api.content.get(UID=self.uuid)
        if not self.document or not self.document.file:
            raise NotFound
        return {
            'content-type': self.document.file.contentType,
            'csrf-token': createToken(),
            'document-url': self.document.absolute_url(),
            'download': 'download_file_version',
            'filename': self.document.get_filename(),
            }

    def render(self):
        self.request.response.setHeader('Content-type', 'application/json')
        return json.dumps(self.get_base_payload())


class OfficeConnectorAttachPayload(OfficeConnectorPayload):
    """Issue JSON instruction payloads for OfficeConnector.

    Consists of the minimal instruction set with which to perform an attach to
    email action.
    """

    def render(self):
        self.request.response.setHeader('Content-type', 'application/json')
        return json.dumps(self.get_base_payload())


class OfficeConnectorCheckoutPayload(OfficeConnectorPayload):
    """Issue JSON instruction payloads for OfficeConnector.

    Consists of the minimal instruction set with which to perform a full
    checkout checkin cycle for a file attached to a document.
    """

    def render(self):
        payload = self.get_base_payload()

        # A permission check to verify the user is also able to upload
        if not api.user.has_permission('Modify portal content',
                                       obj=self.document):
            raise Forbidden

        payload['checkin-with-comment'] = '@@checkin_document'
        payload['checkin-without-comment'] = 'checkin_without_comment'
        payload['checkout'] = '@@checkout_documents'
        payload['edit-form'] = 'edit'

        self.request.response.setHeader('Content-type', 'application/json')
        return json.dumps(payload)