from changes.config import db
from changes.models.author import Author


class AuthorValidator(object):
    def __call__(self, value):
        parsed = self.parse(value)
        if not parsed:
            raise ValueError(value)

        name, email = parsed
        try:
            return Author.query.filter_by(email=email)[0]
        except IndexError:
            author = Author(email=email, name=name)
            db.session.add(author)
            return author

    def parse(self, label):
        import re
        match = re.match(r'^(.+) <([^>]+)>$', label)
        if not match:
            return
        return match.group(1), match.group(2)
