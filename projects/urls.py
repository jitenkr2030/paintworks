"""Projects URLs."""
from django.urls import path
from . import views

app_name = "projects"

urlpatterns = [
    path("", views.project_list, name="list"),
    path("new/", views.project_create, name="create"),
    path("mine/tasks/", views.worker_my_tasks, name="my_tasks"),
    path("<int:pk>/", views.project_detail, name="detail"),
    path("<int:pk>/tasks/new/", views.project_add_task, name="add_task"),
    path("<int:pk>/tasks/<int:task_pk>/status/", views.project_task_status, name="task_status"),
    path("<int:pk>/reports/new/", views.project_add_report, name="add_report"),
    path("<int:pk>/photos/", views.project_upload_photo, name="upload_photo"),
    path("<int:pk>/completion/", views.project_completion, name="completion"),
    path("<int:pk>/timeline/", views.project_timeline, name="timeline"),
]
