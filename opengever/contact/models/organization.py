from opengever.base.model import CONTENT_TITLE_LENGTH
from opengever.contact.models.contact import Contact
from opengever.contact.models.org_role import OrgRole
from opengever.ogds.models.types import UnicodeCoercingText
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship


class Organization(Contact):

    __tablename__ = 'organizations'

    organization_id = Column('id', Integer,
                             ForeignKey('contacts.id'), primary_key=True)
    contact_type = Column(String(20), nullable=False)
    name = Column(String(CONTENT_TITLE_LENGTH), nullable=False)
    description = Column(UnicodeCoercingText)

    persons = relationship("OrgRole", back_populates="organization")

    __mapper_args__ = {'polymorphic_identity': 'organization'}