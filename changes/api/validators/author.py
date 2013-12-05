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

    def parse(self, value):
        import re
        match = re.match(r'^(.+) <([^>]+)>$', value)

        if not match:
            if '@' in value:
                name, email = value, value
            else:
                raise ValueError(value)
        else:
            name, email = match.group(1), match.group(2)
        return name, email
