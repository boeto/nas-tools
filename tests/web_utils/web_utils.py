from web.backend.web_utils import WebUtils


webUtils = WebUtils()


class _TestWebUtils:
    def _test_get_current_version(self):
        current_version = webUtils.get_current_version()
        assert current_version is not None

    def _test_get_latest_version(self):
        latest_version = webUtils.get_latest_version()
        assert latest_version is not None
