from django.shortcuts import render
from django.http.response import HttpResponse


from . import models

# Create your views here.

def home(request):
    """Display the home page."""
    return render(request,
                  'home.html')

def about(request):
    """Provide more information about the reason for the programs existence and 
    who wrote it."""
    return HttpResponse("Placeholder")

def programs(request):
    """Display a list of degree programs at EvCC and their associated 
    information page links."""
    programs = models.DegreeProgram.objects.all()
    return render(request,
                  'programs.html',
                  {"programs":programs})

def degree_program(request, pid):
    """Given a degree program, show the following information:

    - Program name, number of credit hours, later a description if one is available
    - What courses are involved in this degree and their core learning outcomes
    - A comparison of the curriculum similarity this degree program has to every other degree program"""
    ref_degree_program_id = pid
    rdp_object = models.DegreeProgram.objects.get(id=ref_degree_program_id)
    # Get courses in program
    courses = models.Course.objects.filter(
        dpcoursespecific__degree_program=ref_degree_program_id)
    course_clo_pairs = []
    for course in courses:
        course_outcomes = [False] * models.CoreLearningOutcome.objects.all().count()
        clo_raw = models.CoreLearningOutcome.objects.filter(
            courselearningoutcome__course=course).order_by("id")
        for outcome_placeholder in enumerate(course_outcomes):
            if clo_raw.filter(id=outcome_placeholder[0]).exists():
                course_outcomes[outcome_placeholder[0]] = True
        course_clo_pairs.append((course, course_outcomes))
    # Get program distances
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
                   "course_clo_pairs":course_clo_pairs,
                   "program_distances":program_distances})

def outcomes(request):
    """Return a list of core learning outcomes and links to their associated pages."""
    outcomes = models.CoreLearningOutcome.objects.all()
    return render(request,
                  'outcomes.html',
                  {"outcomes":outcomes})

def clo(request, clo_id):
    """Given a core learning outcome, show the following information:

    - Label, description.
    - How many total classes use this core learning outcome.
    - What classes in specific use this core learning outcome.
    - Degree Programs sorted by which ones use this core learning outcome most to least."""
    return HttpResponse("Placeholder.")
