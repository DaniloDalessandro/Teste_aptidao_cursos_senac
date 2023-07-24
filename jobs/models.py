from django.db import models

# Create your models here.

class Job(models.Model):
    LEVEL_CHOICES = (
        ('ba', 'Básico'),
        ('in', 'Intermediário'),
        ('av', 'Avançado'),
    )

    title = models.CharField(max_length=100,verbose_name='Título do curso')
    description = models.TextField(verbose_name='Descrição do curso')
    requirements = models.TextField(verbose_name='Pré-requisito do curso')
    responsibilities = models.TextField(verbose_name='Responsabilidades')
    level = models.CharField(max_length=2, choices=LEVEL_CHOICES, verbose_name='Nivel')
    skills = models.ManyToManyField("jobs.Skill", related_name="jobs",verbose_name='Skills necessárias')

    def __str__(self):
        return self.title
    
    def requirements_list(self):
        return self.requirements.split("\n")
    
    def responsibilities_list(self):
        return self.responsibilities.split("\n")


class Skill(models.Model):
    title = models.CharField(max_length=100, unique=True, blank=False, null=False)

    def __str__(self):
        return self.title
    
