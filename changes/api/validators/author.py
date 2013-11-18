from changes.models.author import Author
from changes.db.utils import get_or_create


class AuthorValidator(object):
    def __call__(self, value):
        parsed = self.parse(value)
        if not parsed:
            raise ValueError(value)

        name, email = parsed
        author, _ = get_or_create(Author, where={
            'email': email,
        }, defaults={
            'name': name,
        })
        return author

    def parse(self, label):
        import re
        match = re.match(r'^(.+) <([^>]+)>$', label)
        if not match:
            return
        return match.group(1), match.group(2)
