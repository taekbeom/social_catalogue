from django.shortcuts import render
from django.http import HttpResponse
from .models import Post, News


def home(request):
    content = {
        "title": "Home",
        "news_list": News.objects.all()
    }
    return render(request, 'catalogue/home.html', content)


def profile(request):
    content = {
        "title": "Profile",
        "posts": Post.objects.all()
    }
    return render(request, 'catalogue/profile.html', content)


def catalogue(request):
    content = {
        "title": "Catalogue"
    }
    return render(request, 'catalogue/catalogue.html', content)


def login(request):
    content = {
        "title": "Log In"
    }
    return render(request, 'catalogue/login.html', content)


def signup(request):
    content = {
        "title": "Sign Up"
    }
    return render(request, 'catalogue/signup.html', content)
