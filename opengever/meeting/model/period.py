from opengever.base.model import Base
from opengever.globalindex.model import WORKFLOW_STATE_LENGTH
from opengever.meeting import _
from opengever.meeting.workflow import State
from opengever.meeting.workflow import Transition
from opengever.meeting.workflow import Workflow
from plone import api
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Sequence


class Period(Base):

    STATE_ACTIVE = State('active', is_default=True,
                         title=_('active', default='Active'))
    STATE_CLOSED = State('closed', title=_('closed', default='Closed'))

    workflow = Workflow([
        STATE_ACTIVE,
        STATE_CLOSED,
        ], [
        Transition('active', 'closed',
                   title=_('close_period', default='Close period')),
        ])

    __tablename__ = 'periods'

    period_id = Column('id', Integer, Sequence('periods_id_seq'),
                       primary_key=True)
    committee_id = Column('committee_id', Integer, ForeignKey('committees.id'),
                          nullable=False)
    committee = relationship('Committee', backref='periods')
    workflow_state = Column(String(WORKFLOW_STATE_LENGTH), nullable=False,
                            default=workflow.default_state.name)
    title = Column(String(256), nullable=False)
    date_from = Column(Date, nullable=False)
    date_to = Column(Date, nullable=False)
    decision_sequence_number = Column(Integer, nullable=False, default=0)
    meeting_sequence_number = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return '<Period {}>'.format(repr(self.title))

    def is_editable(self):
        return True

    def is_removable(self):
        return False

    def get_title(self):
        return u'{} ({} - {})'.format(
            self.title, self.get_date_from(), self.get_date_to())

    def get_url(self, context, view=None):
        # XXX move to sqlformsupport
        return "{}/period-{}".format(context.absolute_url(), self.period_id)

    def get_date_from(self):
        """Return a localized date."""

        return api.portal.get_localized_time(datetime=self.date_from)

    def get_date_to(self):
        """Return a localized date."""

        return api.portal.get_localized_time(datetime=self.date_to)

    def execute_transition(self, name):
        self.workflow.execute_transition(self, self, name)

    def can_execute_transition(self, name):
        return self.workflow.can_execute_transition(self, name)

    def get_edit_values(self, fieldnames):
        values = {}
        for fieldname in fieldnames:
            value = getattr(self, fieldname, None)
            if value:
                values[fieldname] = value

        return values

    def update_model(self, data):
        for key, value in data.items():
            setattr(self, key, value)

    def get_next_decision_sequence_number(self):
        self.decision_sequence_number += 1
        return self.decision_sequence_number

    def get_next_meeting_sequence_number(self):
        self.meeting_sequence_number += 1
        return self.meeting_sequence_number
