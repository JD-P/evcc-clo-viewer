from django.shortcuts import render
from django.http.response import HttpResponse


from . import models

# Create your views here.

def degree_program(request):
    """Given a degree program, show the following information:

    - Program name, number of credit hours, later a description if one is available
    - What courses are involved in this degree and their core learning outcomes
    - A comparison of the curriculum similarity this degree program has to every other degree program"""
    ref_degree_program_id = 80 # Hardcoded during testing, but will be from form
    rdp_object = models.DegreeProgram.objects.get(id=ref_degree_program_id)
    program_distances = []
    for degree_program in models.DegreeProgram.objects.exclude(
            id=ref_degree_program_id):
        union = models.Course.objects.none().union(
            models.DPCourseSpecific.objects.filter(
                degree_program=ref_degree_program_id),
            models.DPCourseSpecific.objects.filter(
                degree_program=degree_program.id)).count()
        overlap = models.Course.objects.filter(
            dpcoursespecific__degree_program__id=ref_degree_program_id).filter(
                dpcoursespecific__degree_program__id=degree_program.id).count()
        program_distances.append((degree_program, (overlap / union) * 100))
    program_distances.sort(key=lambda distance: distance[1])
    
    return render(request,
                  'degree_program.html',
                  {"reference_program":rdp_object,
                   "program_distances":program_distances})
