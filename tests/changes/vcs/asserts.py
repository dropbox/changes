from __future__ import absolute_import

from unittest import TestCase


class VcsAsserts(TestCase):
    def assertRevision(self, revision, author=None, message=None, subject=None,
                       branches=None):
        """ Asserts values of the given fields in the provided revision.

        :param revision: The revision to validate
        :param author: that must be present in the ``revision``
        :param message: message substring that must be present in ``revision``
        :param subject: exact subject that must be present in the ``revision``
        :param branches: all the branches that must be in the ``revision``
        """
        if author:
            self.assertEquals(author, revision.author)
        if message:
            self.assertIn(message, revision.message)
        if subject:
            self.assertIn(subject, revision.subject)
        if branches:
            self.assertListEqual(branches, revision.branches)
