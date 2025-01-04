from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from posts.core import PostCreateForm

from .models import *


def home_view(request: HttpRequest) -> HttpResponse:
    """
    Render the home page with a list of all posts.

    This view queries all `Post` objects from the database and passes them
    to the `home.html` template for rendering. The template can then display
    the list of posts dynamically.

    Args:
        request (HttpRequest): The HTTP request object containing metadata about the request.

    Returns:
        HttpResponse: A rendered HTML response containing the list of posts.
    """
    posts = Post.objects.all()
    return render(request, "posts/home.html", {"posts": posts})


def post_create_view(request: HttpRequest) -> HttpResponse:
    """
    Render the post creation page with a form.

    This view renders the `post_create.html` template, which contains a form
    for creating a new post. The form is initialized using the `PostCreateForm`
    class, which is bound to the `Post` model.

    Args:
        request (HttpRequest): The HTTP request object containing metadata about the request.

    Returns:
        HttpResponse: A rendered HTML response for the post creation page, with the form
        context included for user input.
    """
    form = PostCreateForm()

    if request.method == "POST":
        form = PostCreateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("home")

    return render(request, "posts/post_create.html", {"form": form})
