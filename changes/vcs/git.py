from __future__ import absolute_import, division, print_function

from .base import Vcs, Revision


class GitVcs(Vcs):
    binary_path = 'git'

    def clone(self):
        self.run([self.binary_path, 'clone', self.url, self.path])

    def update(self):
        self.run([self.binary_path, 'fetch', '--all'])
        self.run([self.binary_path, 'remote', 'prune', 'origin'])

    def get_revision(self, id):
        result = self.run([self.binary_path, 'log', id, '-n 1', '--pretty=format:%H\n%an <%ae>\n%B'])

        sha, author, message = result.split('\n', 2)

        return Revision(
            id=sha,
            author=author,
            message=message,
        )
