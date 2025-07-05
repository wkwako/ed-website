from django.db import models
from django.contrib.auth.models import User


class UserHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem_text = models.TextField()
    difficulty = models.CharField(max_length=10, choices=[("Easy", "Easy"), ("Medium", "Medium"), ("Hard", "Hard")])
    is_correct = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)
    problem_type = models.CharField(max_length=20, default="None", choices=[("determine_output", "Determine output"), ("fill_in_vars", "Rename functions"), ("drag_and_drop", "Drag and drop")])
    problem_hash = models.CharField(max_length=64, db_index=True, default='')