from changes.testutils import TestCase
from changes.utils import phabricator_utils


class PhabUtilsTest(TestCase):

    def test_is_iden(self):
        candidates = {
            "rREPOabcd": True,

            "r": False,
            "rREP": False,
            "rrREPOabcd": False,
            "rRePabcd": False,
            "rREPabCd": False,
            "rREPab#d": False,
            "oREPabcd": False,
            "rRab0d": True,
            "rR0ab": True,
        }

        errmsg = "might_be_diffusion_iden failed with string %s"
        for term in candidates:
            expected = candidates[term]
            observed = phabricator_utils.might_be_diffusion_iden(term)
            assert expected == observed, errmsg % term

    def test_get_hash(self):
        identifiers = {
            "rREPOabcd": "abcd",
            "rR0ab": "0ab",
        }

        errmsg = "get_hash_from_diffusion_iden failed with string %s"
        for term in identifiers:
            expected = identifiers[term]
            observed = phabricator_utils.get_hash_from_diffusion_iden(term)
            assert expected == observed, errmsg % term
