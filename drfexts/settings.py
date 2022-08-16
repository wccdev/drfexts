# http://www.django-rest-framework.org/api-guide/settings/
REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": [
        "permissions.IsAuthenticatedWriteOrReadOnly",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # 'oauth2_provider.contrib.rest_framework.OAuth2Authentication',  # Own oauth server
        "client_authentication.ApiTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    # Enable DRF pagination
    # 'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    "DEFAULT_PAGINATION_CLASS": "drf_defaults.DefaultResultsSetPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_RENDERER_CLASSES": (
        # 'rest_framework.renderers.JSONRenderer',  # Swapping out the original renderer
        "lib.drf_renderer.UJSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        # 'rest_framework.parsers.JSONParser',  # Swapping out the original parser
        "lib.drf_parser.UJSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
}
