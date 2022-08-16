import os
from urllib.parse import urljoin

from django.conf import settings
from django.utils.encoding import force_text
from storages.backends.s3boto3 import S3Boto3Storage


class NormalizeNameMixin:
    def _normalize_name(self, name):
        # urljoin won't work if name is absolute path
        name = name.lstrip("/")
        base_path = force_text(self.location)
        final_path = urljoin(base_path + "/", name)
        name = os.path.normpath(final_path.lstrip("/"))

        # Add / to the end of path since os.path.normpath will remove it
        if final_path.endswith("/") and not name.endswith("/"):
            name += "/"

        # Store filenames with forward slashes, even on Windows.
        return name.replace("\\", "/")


class AliOSSMediaStorage(NormalizeNameMixin, S3Boto3Storage):
    location = settings.MEDIAFILES_LOCATION
    file_overwrite = False


class AliOSSStaticStorage(NormalizeNameMixin, S3Boto3Storage):
    location = settings.STATICFILES_LOCATION
    file_overwrite = True
