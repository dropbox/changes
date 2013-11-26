from __future__ import absolute_import, division, print_function

from .base import Vcs, Revision


class MercurialVcs(Vcs):
    binary_path = 'hg'

    def clone(self):
        self.run([self.binary_path, 'clone', '--uncompressed', self.url, self.path])

    def update(self):
        self.run([self.binary_path, 'pull'])

    def get_revision(self, id):
        result = self.run([self.binary_path, 'log', '-r %s' % (id,), '--template={node}\n{author}\n{desc}'])

        sha, author, message = result.split('\n', 2)

        return Revision(
            id=sha,
            author=author,
            message=message,
        )
