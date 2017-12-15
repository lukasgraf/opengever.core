from ftw.testbrowser import browsing
from ftw.testbrowser.pages import statusmessages
from opengever.ogds.base.utils import get_current_org_unit
from opengever.testing import IntegrationTestCase
from plone import api


class TestDelegateTaskToInbox(IntegrationTestCase):

    @browsing
    def test_delegate_to_inbox(self, browser):
        self.login(self.secretariat_user, browser)

        browser.open(self.task,
                     view='@@task_transition_controller',
                     data={'transition': 'task-transition-delegate'})

        form = browser.find_form_by_field('Responsibles')
        form.find_widget('Responsibles').fill(
            ['inbox:{}'.format(get_current_org_unit().id())])
        browser.css('#form-buttons-save').first.click()  # can't use submit()

        form = browser.find_form_by_field('Issuer')
        form.find_widget('Issuer').fill(self.dossier_responsible.getId())

        browser.css('#form-buttons-save').first.click()  # can't use submit()

        self.assertEqual(['1 subtasks were create.'],
                         statusmessages.info_messages())


class TestDelegateTaskForm(IntegrationTestCase):

    @browsing
    def test_delegate_creates_subtask(self, browser):
        self.login(self.regular_user, browser=browser)

        browser.open(self.task, view='delegate_recipients')

        # step 1
        form = browser.find_form_by_field('Responsibles')
        form.find_widget('Responsibles').fill('fa:robert.ziegler')
        browser.css('#form-buttons-save').first.click()

        # step 2
        browser.css('#form-buttons-save').first.click()

        self.assertEqual(['1 subtasks were create.'],
                         statusmessages.info_messages())

        subtask = self.task.objectValues()[-1]
        self.assertEqual(self.task.title, subtask.title)
        self.assertEqual('robert.ziegler', subtask.responsible)
        self.assertEqual('fa', subtask.responsible_client)
        self.assertEqual('task-state-open', api.content.get_state(subtask))

