from opengever.meeting.command import MIME_DOCX
from opengever.meeting.sablon import Sablon
from Products.Five.browser import BrowserView
import json


SAMPLE_MEETING_DATA = {
    '_sablon': {'properties': {'start_page_number': 42}},
    'agenda_items': [{
        'description': u'Strafbefehl wegen Bauens ohne Bewilligung',
        'dossier_reference_number': u'Client1 1 / 1',
        'repository_folder_title': u'Strafwesen',
        'number': '1.',
        'title': u'Strafbefehl wegen Bauens ohne Bewilligung',
        'is_paragraph': False,
        'decision_number': 1,
        'attachments': [{
            "title": u'Beweisaufn\xe4hme',
            "filename": u"beweisaufnahme.txt"
            }, {
            "title": u"L\xf6rem",
            "filename": u"lorem.eml"
            }, {
            "title": "Strafbefehl"
            }]
    }, {
        'description': u'R\xfccktritt Hans Muster',
        'dossier_reference_number': None,
        'repository_folder_title': None,
        'number': '2.',
        'title': u'R\xfccktritt Hans Muster',
        'is_paragraph': False,
        'decision_number': 2}],
    'mandant': {'name': u'Client1'},
    'meeting': {'date': u'Dec 13, 2011',
                'end_time': u'11:45 AM',
                'start_time': u'09:30 AM',
                'number': 11,
                'location': u'B\xe4rn'},
    'committee': {'name': u'Gemeinderat'},
    'participants': {
        'presidency': {'firstname': 'Peter',
                       'lastname': u'M\xfcller',
                       'fullname': u'M\xfcller Peter',
                       'email': None,
                       'role': u'F\xfcrst'},
        'secretary': {'firstname': u'C\xf6mmittee',
                      'lastname': 'Secretary',
                      'fullname': u'Secretary C\xf6mmittee',
                      'email': 'committee.secretary@example.com'},
        'members': [
                    {'firstname': 'Anna',
                     'lastname': u'B\xe4nni',
                     'fullname': u'B\xe4nni Anna',
                     'role': None,
                     'email': u'baenni@example.com'},
                    {'email': u'mueller@example.com',
                     'firstname': u'Franz',
                     'fullname': u'M\xfcller Franz',
                     'lastname': u'M\xfcller',
                     'role': None},
                    ],
        'other': [u'Hans M\xfcller', u'Heidi Muster']},
    'protocol': {'type': u'Protocol'}}


class FillMeetingTemplate(BrowserView):
    """View to fill a template with sample data for a meeting."""

    def __call__(self):
        sablon = Sablon(self.context)
        sablon.process(json.dumps(SAMPLE_MEETING_DATA))
        assert sablon.is_processed_successfully(), sablon.stderr

        response = self.request.response
        response.setHeader('X-Theme-Disabled', 'True')
        response.setHeader('Content-Type', MIME_DOCX)
        response.setHeader("Content-Disposition",
                           'attachment; filename="{}"'.format('template.docx'))
        return sablon.file_data
