from ftw.mail.interfaces import IEmailAddress
from opengever.document.events import FileAttachedToEmailEvent
from opengever.dossier.events import DossierAttachedToEmailEvent
from opengever.officeconnector.helpers import create_oc_url
from opengever.officeconnector.helpers import is_officeconnector_attach_feature_enabled  # noqa
from opengever.officeconnector.helpers import is_officeconnector_checkout_feature_enabled  # noqa
from plone import api
from plone.protect import createToken
from plone.rest import Service
from zExceptions import Forbidden
from zExceptions import NotFound
from zope.event import notify

import json


class OfficeConnectorURL(Service):
    """Create oc:<JWT> URLs for javascript to fetch and pass to the OS."""

    def create_officeconnector_url_json(self, payload):
        self.request.response.setHeader('Content-Type', 'application/json')

        url = create_oc_url(self.request, self.context, payload)

        if url:
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
        return self.create_officeconnector_url_json(payload)


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

        return self.create_officeconnector_url_json(payload)


class OfficeConnectorPayload(Service):
    """Issue JSON instruction payloads for OfficeConnector."""

    def __init__(self, context, request):
        super(OfficeConnectorPayload, self).__init__(context, request)
        self.uuids = json.loads(request['BODY'])

    def get_base_payloads(self):
        # Require an authenticated user
        if api.user.is_anonymous():
            raise Forbidden

        documents = []
        for uuid in self.uuids:
            document = api.content.get(UID=uuid)
            if document and document.has_file():
                documents.append(document)

        if not documents:
            raise NotFound

        payloads = []
        for document in documents:
            payloads.append(
                {
                    'content-type': document.get_file().contentType,
                    'csrf-token': createToken(),
                    'document-url': document.absolute_url(),
                    'document': document,
                    'download': 'download',
                    'filename': document.get_filename(),
                    }
                )

        return payloads

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
        payloads = self.get_base_payloads()

        dossier_notifications = {}

        for payload in payloads:
            document = payload['document']
            parent_dossier = document.get_parent_dossier()

            if parent_dossier:
                # XXX - this should be unnecessary with dossier journaling
                if parent_dossier.is_open():
                    payload['bcc'] = IEmailAddress(
                        self.request).get_email_for_object(parent_dossier)

                parent_dossier_uuid = api.content.get_uuid(parent_dossier)

                if parent_dossier_uuid not in dossier_notifications:
                    dossier_notifications[parent_dossier_uuid] = []

                dossier_notifications[parent_dossier_uuid].append(document)

            payload['title'] = document.title_or_id()
            del payload['document']
            notify(FileAttachedToEmailEvent(document))

        for uuid, documents in dossier_notifications.iteritems():
            dossier = api.content.get(UID=uuid)
            notify(DossierAttachedToEmailEvent(dossier, documents))

        return json.dumps(payloads)


class OfficeConnectorCheckoutPayload(OfficeConnectorPayload):
    """Issue JSON instruction payloads for OfficeConnector.

    Consists of the minimal instruction set with which to perform a full
    checkout checkin cycle for a file attached to a document.
    """

    def render(self):
        payloads = self.get_base_payloads()

        # Upload API will be included as a registry setting in the future when
        # the plone.api endpoint gets made - for now we've made a custom upload
        # form.
        for payload in payloads:
            payload['checkin-with-comment'] = '@@checkin_document'
            payload['checkin-without-comment'] = 'checkin_without_comment'
            payload['checkout'] = '@@checkout_documents'
            payload['upload-form'] = 'file_upload'
            payload['upload-api'] = None

            # A permission check to verify the user is also able to upload
            if not api.user.has_permission('Modify portal content',
                                           obj=payload['document']):
                raise Forbidden

            del payload['document']

        self.request.response.setHeader('Content-type', 'application/json')

        return json.dumps(payloads)
