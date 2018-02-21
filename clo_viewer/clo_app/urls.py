from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.home, name="home"),
    url(r'^about/$', views.about, name="about"),
    url(r'^programs/$', views.programs, name="programs"),
    url(r'^outcomes/$', views.outcomes, name="outcomes"),
    url(r'^degreeprogram/(?P<pid>[0-9]+)$', views.degree_program, name="degree-program"),
    url(r'^clo/(?P<clo_id>[0-9]+)$', views.clo, name="clo"),
]
