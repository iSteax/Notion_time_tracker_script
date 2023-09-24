from django.db import models


class TaskTable(models.Model):
    task_id = models.TextField(primary_key=True)
    task_name = models.TextField()
    start_time = models.TextField(null=True, blank=True)
    paused_time = models.TextField(null=True, blank=True)
    elapsed_time = models.TextField(null=True, blank=True)
    done_time = models.TextField(null=True, blank=True)
    status = models.TextField()
    previous_status = models.TextField(null=True, blank=True)

