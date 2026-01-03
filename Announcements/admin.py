from django.contrib import admin
from Announcements.models import Task, Announcements, Reply, AnnouncementsRequest, Reposts, Text, Choice, Pin, FileResponse, CompletedTask, Question, QuestionResponse, SubQuestion, TaskResponse, Reaction, Comment
# Register your models here.

admin.site.register(Task)
admin.site.register(Announcements)
admin.site.register(Reply)
admin.site.register(AnnouncementsRequest)
admin.site.register(Reposts)
admin.site.register(Text)
admin.site.register(Choice)
admin.site.register(Pin)
admin.site.register(FileResponse)
admin.site.register(CompletedTask)
admin.site.register(Question)
admin.site.register(SubQuestion)
admin.site.register(QuestionResponse)
admin.site.register(TaskResponse)
admin.site.register(Reaction)
admin.site.register(Comment)