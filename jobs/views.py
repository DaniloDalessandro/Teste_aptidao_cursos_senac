from django.shortcuts import render,get_object_or_404
from .models import Job
# Create your views here.

def list_jobs(request):
    return render(
        request,
        "jobs/list.html",
        {
            "page_title": "Lista de cursos - Senac  ",
            "jobs": Job.objects.all()
        }
    )

def details_job(request,pk):
    job = get_object_or_404(Job,pk=pk)
    return render(
        request,
        "jobs/details.html",
        {
            "page_title": job.title,
            "job":job
        }
    )