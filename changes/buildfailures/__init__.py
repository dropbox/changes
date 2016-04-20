from changes.buildfailures.duplicatetestname import DuplicateTestName
from changes.buildfailures.malformedartifact import MalformedArtifact
from changes.buildfailures.malformedmanifestjson import MalformedManifestJson
from changes.buildfailures.missingartifact import MissingArtifact
from changes.buildfailures.missingmanifestjson import MissingManifestJson
from changes.buildfailures.missingtests import MissingTests
from changes.buildfailures.testfailure import TestFailure
from changes.buildfailures.timeout import Timeout

registry = {
    'duplicate_test_name': DuplicateTestName(),
    'malformed_artifact': MalformedArtifact(),
    'malformed_manifest_json': MalformedManifestJson(),
    'missing_artifact': MissingArtifact(),
    'missing_manifest_json': MissingManifestJson(),
    'missing_tests': MissingTests(),
    'test_failures': TestFailure(),
    'timeout': Timeout(),
}
