from django.db import models
from django.db.models.functions import Coalesce


class CommonStatus(models.IntegerChoices):
    DELETED = 0, "已删除"
    TO_VALID = 10, "待生效"
    VALID = 50, "已生效"
    TO_INVALID = 75, "待失效"
    INVALID = 100, "已失效"


class AuditStatus(models.IntegerChoices):
    TO_AUDIT = 1, "提交审核"
    PASSED = 10, "审核通过"
    REJECTED = 11, "审核拒绝"
    TO_AUDIT_LEVEL2 = 2, "提交审核"
    PASSED_LEVEL2 = 20, "审核通过"
    REJECTED_LEVEL2 = 21, "审核拒绝"
    TO_AUDIT_LEVEL3 = 3, "提交审核"
    PASSED_LEVEL3 = 30, "审核通过"
    REJECTED_LEVEL3 = 31, "审核拒绝"
