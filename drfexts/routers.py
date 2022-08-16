from rest_framework.routers import DefaultRouter


class OptionalSlashRouter(DefaultRouter):
    """
    Providing optional tailing slash for the router.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trailing_slash = "/?"
