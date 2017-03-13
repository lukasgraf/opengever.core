from five import grok
from opengever.base.interfaces import IRedirector
from plone.app.layout.viewlets.interfaces import IAboveContentTitle
from zope.interface import Interface
from zope.publisher.interfaces.browser import IBrowserRequest
import json


REDIRECTOR_SESS_KEY = 'opengever_base_IRedirector'
REDIRECTOR_COOKIE_NAME = 'ogredirect'


class RedirectorCookie(object):
    """Manages setting and getting the cookie, containing a list of redirect items.
    """

    def __init__(self, request):
        self.request = request

    def add(self, item):
        self._set(self._get() + [item])

    def read(self, remove=True):
        value = self._get()
        if remove:
            self._set([])
        return value

    def _get(self):
        # Load from response cookie in case this request added or updated the
        # cookie
        cookie = self.request.response.cookies.get(REDIRECTOR_COOKIE_NAME, {})
        value = cookie.get('value', None)
        if value == 'deleted':
            value = None

        # Load from request cookie in case a prior request added the cookie
        if not value:
            value = self.request.get(REDIRECTOR_COOKIE_NAME)

        if value:
            return json.loads(value)
        else:
            return []

    def _set(self, cookies):
        if cookies:
            self.request.response.setCookie(REDIRECTOR_COOKIE_NAME,
                                            json.dumps(cookies),
                                            path='/')
        else:
            self.request.response.expireCookie(REDIRECTOR_COOKIE_NAME,
                                               path='/')


class Redirector(grok.Adapter):
    """An adapter for the BrowserRequest to redirect a user after loading the
    next page to a specific URL which is opened in another window / tab with
    the name "target".
    """

    grok.provides(IRedirector)
    grok.context(IBrowserRequest)

    def __init__(self, request):
        self.request = request

    def redirect(self, url, target='_blank', timeout=0):
        """Redirects the user to a `url` which is opened in a window called
        `target` after loading the next page.
        """
        RedirectorCookie(self.request).add({'url': url,
                                            'target': target,
                                            'timeout': int(timeout)})

    def get_redirects(self, remove=True):
        """Returns a list of dicts containing the redirect informations.
        """
        return RedirectorCookie(self.request).read(remove=remove)


class RedirectorViewlet(grok.Viewlet):
    """Viewlet which adds the redirects for the IRedirector."""

    grok.name('redirector')
    grok.context(Interface)
    grok.viewletmanager(IAboveContentTitle)
    grok.require('zope2.View')

    JS_TEMPLATE = '''
<script type="text/javascript" class="redirector">
$(function() {
    window.setTimeout("window.open('%(url)s', '%(target)s');", %(timeout)s);
});
</script>
'''

    def view_name(self):
        view = getattr(self, 'view', None)
        if view:
            return getattr(view, '__name__', None)

    def render(self):
        redirector = IRedirector(self.request)

        # If we're on the CSRF confirm-action dialog, we don't want to
        # trigger any redirects.
        if self.view_name() == 'confirm-action':
            # Consume the redirector cookie to avoid unconditional redirects
            # immediately *after* the confirm-action view. If the user
            # confirms, the redirector cookies will be set again.
            redirector.get_redirects(remove=True)
            return ''

        redirects = redirector.get_redirects(remove=True)
        html = []
        for redirect in redirects:
            html.append(RedirectorViewlet.JS_TEMPLATE % redirect)

        return ''.join(html)
