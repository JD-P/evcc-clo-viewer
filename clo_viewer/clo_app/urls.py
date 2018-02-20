from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.home, name="home"),
    url(r'^programs/$', views.programs, name="programs"),
    url(r'^degreeprogram/(?P<pid>[0-9]+)$', views.degree_program, name="degree-program"),
]
