from five import grok
from opengever.tabbedview.browser.tabs import OpengeverListingTab, OpengeverSolrListingTab
from zope.component import queryUtility
from ftw.table import helper
from opengever.tabbedview import helper as opengever_helper
from opengever.tabbedview.helper import readable_ogds_author
from opengever.octopus.tentacle.contacts import ContactInformation
from ftw.task import _

def authenticated_member(context):
    return context.portal_membership.getAuthenticatedMember().getId()
    
def linked(item, value):
    url_method = lambda: '#'
    #item = hasattr(item, 'aq_explicit') and item.aq_explicit or item
    if hasattr(item, 'getURL'):
        url_method = item.getURL
    elif hasattr(item, 'absolute_url'):
        url_method = item.absolute_url
    img = u'<img src="%s"/>' % (item.getIcon)
    link = u'<a href="%s" >%s%s</a>' % (url_method(), img, value) 
    wrapper = u'<span class="linkWrapper">%s</span>' % link
    return wrapper
    

class MyTasks(OpengeverSolrListingTab):
    grok.name('tabbedview_view-mytasks_solr')
    columns= (
        ('', helper.draggable),
        ('', helper.path_checkbox),
        ('review_state', 'review_state', helper.translated_string()),
        ('Title', 'sortable_title', linked),
        {'column' : 'task_type', 
        'column_title' : _(u'label_task_type', 'Task Type')},
        ('deadline', helper.readable_date),
        ('date_of_completion', helper.readable_date), # erledigt am
        {'column' : 'responsible', 
        'column_title' : _(u'label_responsible_task', 'Responsible'),  
        'transform' : readable_ogds_author},
        ('issuer', readable_ogds_author), # zugewiesen von
        {'column' : 'created', 
        'column_title' : _(u'label_issued_date', 'issued at'),
        'transform': helper.readable_date },
        )

    types = ['ftw.task.task', ]
    
    search_options = {'responsible': authenticated_member}


class IssuedTasks(OpengeverSolrListingTab):
    grok.name('tabbedview_view-issuedtasks_solr')
    columns= (
        ('', helper.draggable),
        ('', helper.path_checkbox),
        ('review_state', 'review_state', helper.translated_string()),
        ('Title', 'sortable_title', linked),
        {'column' : 'task_type', 
        'column_title' : _(u'label_task_type', 'Task Type')},
        ('deadline', helper.readable_date),
        ('date_of_completion', helper.readable_date), # erledigt am
        {'column' : 'responsible', 
        'column_title' : _(u'label_responsible_task', 'Responsible'),  
        'transform' : readable_ogds_author},
        ('issuer', readable_ogds_author), # zugewiesen von
        {'column' : 'created', 
        'column_title' : _(u'label_issued_date', 'issued at'),
        'transform': helper.readable_date },
        )
    
    def build_query(self):
        aid = authenticated_member(self.context)
        return 'portal_type:ftw.task.task AND issuer:%s AND ! responsible:%s' % (aid, aid)

        
class AssignedTasks(OpengeverSolrListingTab):
    grok.name('tabbedview_view-assignedtasks_solr')
    columns= (
        ('', helper.draggable),
        ('', helper.path_checkbox),
        ('review_state', 'review_state', helper.translated_string()),
        ('Title', 'sortable_title', linked),
        {'column' : 'task_type', 
        'column_title' : _(u'label_task_type', 'Task Type')},
        ('deadline', helper.readable_date),
        ('date_of_completion', helper.readable_date), # erledigt am
        {'column' : 'responsible', 
        'column_title' : _(u'label_responsible_task', 'Responsible'),  
        'transform' : readable_ogds_author},
        ('issuer', readable_ogds_author), # zugewiesen von
        {'column' : 'created', 
        'column_title' : _(u'label_issued_date', 'issued at'),
        'transform': helper.readable_date },
        )

    def build_query(self):
        users = ContactInformation().list_local_users()
        temp = ''
        for user in users:
            temp += '%s OR ' % user
        return 'portal_type:ftw.task.task AND responsible:(%s)' % (temp[:-3])
