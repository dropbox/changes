from uuid import UUID, uuid4

from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy import or_

from changes.config import db
from changes.db.types.guid import GUID


class Author(db.Model):
    """
    A list of every person who has written a revision parsed by changes.
    Keyed by email. Automatically updated when new authors are seen by
    changes in diffs etc.
    """
    __tablename__ = 'author'

    id = Column(GUID, primary_key=True, default=uuid4)
    name = Column(String(128), nullable=False)
    email = Column(String(128), unique=True)
    date_created = Column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(Author, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid4()

    @classmethod
    def find(cls, author_id, current_user=None):
        if author_id == 'me':
            if current_user is None:
                return []
            email = current_user.email
        elif '@' in author_id:
            email = author_id
        else:
            email = None

        if email:
            username, domain = email.split('@', 1)
            email_query = '{}+%@{}'.format(username, domain)

            return list(cls.query.filter(
                or_(
                    cls.email.like(email_query),
                    cls.email == email,
                )
            ))

        try:
            author_id = UUID(author_id)
        except ValueError:
            return []

        author = cls.query.get(author_id)
        if author is None:
            return []
        return [author]
