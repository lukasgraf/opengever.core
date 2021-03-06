# Copied over from skins/livesearch_reply.py
from ftw.solr.interfaces import ISolrSearch
from ftw.solr.query import escape
from ftw.solr.query import make_query
from opengever.base.solr import OGSolrContentListing
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone import PloneMessageFactory as pmf
from Products.CMFPlone.utils import normalizeString
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser import BrowserView
from Products.PythonScripts.standard import html_quote
from Products.PythonScripts.standard import url_quote_plus
from zope.component import getUtility


USE_ICON = True
MAX_TITLE = 29
MAX_DESCRIPTION = 93


# https://github.com/4teamwork/opengever.core/blob/master/opengever/base/browser/helper.py#L20
def get_mimetype_icon_klass(item):
    # It just makes sense to guess the mimetype of documents
    if not item.portal_type == 'opengever.document.document':
        return 'contenttype-%s' % normalizeString(item.portal_type)

    icon = item.getIcon

    # Fallback for unknown file type
    if icon == '':
        return "icon-document_empty"

    # Strip '.gif' from end of icon name and remove
    # leading 'icon_'
    filetype = icon[:icon.rfind('.')].replace('icon_', '')
    return 'icon-%s' % normalizeString(filetype)


class LiveSearchReplyView(BrowserView):

    def __call__(self):
        self.search_term = self.request.form.get('q', None)
        if not isinstance(self.search_term, unicode):
            self.search_term = self.search_term.decode('utf-8')

        self.limit = self.request.form.get('limit', 10)
        self.path = self.request.form.get('path', None)
        results = self.results()
        return self.render_results(results)

    def results(self):
        if not self.search_term:
            return []

        solr = getUtility(ISolrSearch)
        query = make_query(self.search_term)
        filters = [u'trashed:false']
        if self.path:
            filters.append(u'path_parent:%s' % escape(self.path))
        params = {
            'fl': [
                'UID', 'id', 'Title', 'getIcon', 'portal_type', 'path',
            ],

        }
        resp = solr.search(
            query=query, filters=filters, rows=self.limit, **params)
        return resp

    def render_results(self, resp):
        output = []

        def write(s):
            output.append(safe_unicode(s))

        ts = getToolByName(self.context, 'translation_service')
        portal_url = getToolByName(self.context, 'portal_url')()
        portalProperties = getToolByName(self.context, 'portal_properties')
        siteProperties = getattr(portalProperties, 'site_properties', None)
        useViewAction = []
        if siteProperties is not None:
            useViewAction = siteProperties.getProperty('typesUseViewActionInListings', [])

        results = OGSolrContentListing(resp)
        if not results:
            write('''<fieldset class="livesearchContainer">''')
            write('''<legend id="livesearchLegend">%s</legend>''' % ts.translate(legend_livesearch, context=self.request))
            write('''<div class="LSIEFix">''')
            write('''<div id="LSNothingFound">%s</div>''' % ts.translate(label_no_results_found, context=self.request))
            write('''<div class="LSRow">''')
            write('<a href="%s" style="font-weight:normal">%s</a>' %
                  (portal_url + '/advanced_search?SearchableText=%s' % url_quote_plus(self.search_term),
                   ts.translate(label_advanced_search, context=self.request)))
            write('''</div>''')
            write('''</div>''')
            write('''</fieldset>''')
        else:
            write('''<fieldset class="livesearchContainer">''')
            write('''<legend id="livesearchLegend">%s</legend>''' % ts.translate(legend_livesearch, context=self.request))
            write('''<div class="LSIEFix">''')
            write('''<ul class="LSTable">''')
            for result in results:

                itemUrl = result.getURL()
                if result.portal_type in useViewAction:
                    itemUrl += '/view'

                itemUrl = itemUrl + u'?SearchableText=%s' % url_quote_plus(self.search_term)

                write('''<li class="LSRow">''')
                full_title = safe_unicode(result.Title())
                if len(full_title) > MAX_TITLE:
                    display_title = ''.join((full_title[:MAX_TITLE], '...'))
                else:
                    display_title = full_title

                full_title = full_title.replace('"', '&quot;')

                css_klass = get_mimetype_icon_klass(result.doc)

                write('''<a href="%s" title="%s" class="%s">%s</a>''' % (itemUrl, full_title, css_klass, display_title))
                display_description = safe_unicode(result.Description()) or u''
                if len(display_description) > MAX_DESCRIPTION:
                    display_description = ''.join((display_description[:MAX_DESCRIPTION], '...'))

                # need to quote it, to avoid injection of html containing javascript and other evil stuff
                display_description = html_quote(display_description)
                write('''<div class="LSDescr">%s</div>''' % (display_description))
                write('''</li>''')
                full_title, display_title, display_description = None, None, None

            write('''<li class="LSRow">''')
            write('<a href="%s" style="font-weight:normal">%s</a>' %
                  (portal_url + '/advanced_search?SearchableText=%s' % url_quote_plus(self.search_term),
                   ts.translate(label_advanced_search, context=self.request)))
            write('''</li>''')

            if resp.num_found > self.limit:
                # add a more... row
                write('''<li class="LSRow">''')
                searchquery = u'@@search?SearchableText=%s&path=%s' % (url_quote_plus(self.search_term), self.path)
                write(u'<a href="%s" style="font-weight:normal">%s</a>' % (
                                     searchquery,
                                     ts.translate(label_show_all, context=self.request)))
                write('''</li>''')

            write('''</ul>''')
            write('''</div>''')
            write('''</fieldset>''')
        return '\n'.join(output).encode('utf-8')


legend_livesearch = pmf(
    'legend_livesearch',
    default='LiveSearch &#8595;')
label_no_results_found = pmf(
    'label_no_results_found',
    default='No matching results found.')
label_has_parse_errors = pmf(
    'label_has_parse_errors',
    default='There were errors parsing your query, please note that boolean '
            'expressions like AND, NOT and OR are only allowed in advanced '
            'search.')
label_advanced_search = pmf(
    'label_advanced_search',
    default='Advanced Search&#8230;')
label_show_all = pmf(
    'label_show_all',
    default='Show all items')
