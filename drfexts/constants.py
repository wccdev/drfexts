from django.db import models
from django.db.models.functions import Coalesce


class CommonStatus(models.IntegerChoices):
    DELETED = 0, "已删除"
    TO_VALID = 10, "待生效"
    VALID = 50, "已生效"
    TO_INVALID = 75, "待失效"
    INVALID = 100, "已失效"
