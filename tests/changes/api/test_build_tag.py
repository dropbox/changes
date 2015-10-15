import json

from changes.testutils import APITestCase

NONE = None
NO_TAGS = []
ONE_TAG = ['one_tag']
MULTI_TAGS = ['one_tag', 'two_tags']

TAG_LISTS = [MULTI_TAGS, ONE_TAG, NO_TAGS, NONE]

PATH = '/api/0/builds/{0}/tags'


class BuildTagTest(APITestCase):
    def test_get_tags(self):
        project = self.create_project()

        for tag_list in TAG_LISTS:
            build = self.create_build(project, tags=tag_list)

            path = PATH.format(build.id.hex)
            resp = self.client.get(path)
            data = self.unserialize(resp)

            assert data['tags'] == build.tags

    def test_set_tags(self):
        project = self.create_project()

        # try updating to none, one tag, or two tags
        # from varying start states (none, one tag, or two tags)
        for tag_list_update in TAG_LISTS:
            for tag_list_build in TAG_LISTS:
                build = self.create_build(project, tags=tag_list_build)

                path = PATH.format(build.id.hex)
                self.client.post(path, data={'tags': json.dumps(tag_list_update)})

                resp = self.client.get(path)
                data = self.unserialize(resp)

                if tag_list_update is None:
                    assert data['tags'] == []
                else:
                    assert data['tags'] == tag_list_update

    def test_bad_tag_format(self):
        project = self.create_project()

        tags = {'tags': 'one_tag'}
        build = self.create_build(project, tags=tags)
        path = PATH.format(build.id.hex)

        resp = self.client.post(path, data=tags)
        assert resp.status_code == 400
