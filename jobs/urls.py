from django.urls import path

from .views import list_jobs,details_job

app_name = "jobs"

urlpatterns = [
    path('',list_jobs,name="list"),
    path('<int:pk>/',details_job,name='details')
]