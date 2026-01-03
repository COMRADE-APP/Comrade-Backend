from django.urls import path, include
from Announcements.views import AnnouncementsViewSet, TextViewSet, ReplyViewSet, TaskViewSet, CompletedTaskViewSet, FileResponseViewSet, QuestionViewSet, QuestionResponseViewSet, ChoiceViewSet, SubQuestionViewSet, ReplyViewSet, RepostsViewSet, PinViewSet, TaskResponseViewSet, CommentViewSet, ReactionViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'announcements', AnnouncementsViewSet, basename='announcement')
router.register(r'texts', TextViewSet, basename='text')
router.register(r'replies', ReplyViewSet, basename='reply')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'choices', ChoiceViewSet, basename='choice')
router.register(r'reposts', RepostsViewSet, basename='repost')
router.register(r'pins', PinViewSet, basename='pin')
router.register(r'completed_tasks', CompletedTaskViewSet, basename='completed_task')
router.register(r'file_responses', FileResponseViewSet, basename='file_response')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'sub_questions', SubQuestionViewSet, basename='sub_question')
router.register(r'question_responses', QuestionResponseViewSet, basename='question_response')
router.register(r'task_responses', TaskResponseViewSet, basename='task_response')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'reactions', ReactionViewSet, basename='reaction')



urlpatterns = [
    path('', include(router.urls)),
]