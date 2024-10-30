"""Routes."""

from django.urls import path

from . import views

app_name = "contra"

urlpatterns = [
    path("", views.index, name="index"),
]
