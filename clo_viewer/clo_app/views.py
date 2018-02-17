from django.shortcuts import render
from django.http.response import HttpResponse


from . import models

# Create your views here.

def test_view(request):
    """Given a degree program, determine the distance between it and every other degree program."""
    reference_degree_program = 80 # Hardcoded during testing, but will be from form
    program_distances = []
    for degree_program in models.DegreeProgram.objects.exclude(
            id=reference_degree_program):
        union = models.Course.objects.none().union(
            models.DPCourseSpecific.objects.filter(
                degree_program=reference_degree_program),
            models.DPCourseSpecific.objects.filter(
                degree_program=degree_program.id)).count()
        overlap = models.Course.objects.filter(
            dpcoursespecific__degree_program__id=reference_degree_program).filter(
                dpcoursespecific__degree_program__id=degree_program.id).count()
        program_distances.append((degree_program, (overlap / union) * 100))
    program_distances.sort(key=lambda distance: distance[1])
    
    return render(request,
                  'dp_compare.html',
                  {"program_distances":program_distances})
