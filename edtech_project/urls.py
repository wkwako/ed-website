"""
URL configuration for edtech_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views
from .views import CreateAccount

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("practice/", views.practice, name="practice"),
    path("practice/check-answer/", views.check_answer),
    path("practice/generate-hint/", views.generate_hint),
    path("practice/check-answer-fill-in-vars/", views.check_answer_fill_in_vars),
    path("practice/check-answer-drag-and-drop/", views.check_answer_drag_and_drop),
    path("practice/generate-explanation/", views.generate_explanation),
    path("history/", views.history, name="history"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("create_account/", CreateAccount.as_view(), name="create_account"),
]
