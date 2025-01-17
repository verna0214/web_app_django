import requests
from bs4 import BeautifulSoup
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from posts.core import CommentCreateForm, PostCreateForm, PostEditForm, ReplyCreateForm

from .models import *


def home_view(request: HttpRequest, tag=None) -> HttpResponse:
    """
    Render the home page with a list of posts, optionally filtered by a tag.

    If a tag is provided, the view filters posts to include only those
    associated with the specified tag. Otherwise, it displays all posts.

    Args:
        request (HttpRequest): The HTTP request object containing metadata about the request.
        tag (str, optional): The slug of the tag used to filter posts. Defaults to None.

    Returns:
        HttpResponse: A rendered HTML response displaying the list of posts,
        filtered by the specified tag if provided.
    """
    if tag:
        posts = Post.objects.filter(tags__slug=tag)
        tag = get_object_or_404(Tag, slug=tag)
    else:
        posts = Post.objects.all()

    paginator = Paginator(posts, 3)
    page = int(request.GET.get("page", 1))
    try:
        posts = paginator.page(page)
    except:
        return HttpResponse("")

    context = {"posts": posts, "tag": tag, "page": page}

    if request.htmx:
        return render(request, "snippets/loop_home_posts.html", context)

    return render(request, "posts/home.html", context)


@login_required
def post_create_view(request: HttpRequest) -> HttpResponse:
    """
    Render the post creation page and handle form submissions.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse:
            - A rendered HTML response for the post creation page (GET request).
            - A redirect to the home page upon successful post creation (POST request).

    Key Operations:
        - Fetch metadata (image, title, artist) from the provided URL.
        - Save the data to the `Post` model.

    Dependencies:
        - requests: Fetch external web page content.
        - BeautifulSoup: Parse HTML to extract specific data.
    """
    form = PostCreateForm()

    if request.method == "POST":
        form = PostCreateForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)

            website = requests.get(form.data["url"])
            sourcecode = BeautifulSoup(website.text, "html.parser")

            find_image = sourcecode.select(
                'meta[content^="https://live.staticflickr.com/"]'
            )
            image = find_image[0]["content"]
            post.image = image

            find_title = sourcecode.select("h1.photo-title")
            title = find_title[0].text.strip()
            post.title = title

            find_artist = sourcecode.select("a.owner-name")
            artist = find_artist[0].text.strip()
            post.artist = artist

            post.author = request.user

            post.save()
            form.save_m2m()
            return redirect("home")

    return render(request, "posts/post_create.html", {"form": form})


@login_required
def post_delete_view(request: HttpRequest, pk: str) -> HttpResponse:
    """
    Handle the deletion of a post or raise a 404 error if not found.

    Args:
        request (HttpRequest): The HTTP request object containing metadata about the request.
        pk (str): The primary key (id) of the post to be deleted.

    Returns:
        HttpResponse:
            - A rendered HTML response with the post details for confirmation (GET request).
            - A redirect to the home page upon successful deletion (POST request).

    Raises:
        Http404: If no `Post` object is found with the given primary key.

    Context:
        - `post`: The post instance to be displayed for confirmation.
    """
    post = get_object_or_404(Post, id=pk, author=request.user)

    if request.method == "POST":
        post.delete()
        messages.success(request, "Post deleted")
        return redirect("home")

    return render(request, "posts/post_delete.html", {"post": post})


@login_required
def post_edit_view(request: HttpRequest, pk: str) -> HttpResponse:
    """
    Handle the editing of an existing post or raise a 404 error if not found.

    Args:
        request (HttpRequest): The HTTP request object containing metadata
        about the request.
        pk (str): The primary key (id) of the post to be edited.

    Returns:
        HttpResponse:
            - A rendered form for editing the post (GET request).
            - A redirect to the home page after successfully updating the post (POST request).

    Raises:
        Http404: If no `Post` object is found with the given primary key.
    """
    post = get_object_or_404(Post, id=pk, author=request.user)
    form = PostEditForm(instance=post)

    if request.method == "POST":
        form = PostEditForm(request.POST, instance=post)
        if form.is_valid:
            form.save()
            messages.success(request, "Post updated")
            return redirect("home")

    context = {"post": post, "form": form}
    return render(request, "posts/post_edit.html", context)


def post_page_view(request: HttpRequest, pk: str) -> HttpResponse:
    """
    Display the details of a specific post or raise a 404 error if not found.

    Args:
        request (HttpRequest): The HTTP request object containing metadata
        about the request.
        pk (str): The primary key (id) of the post to display.

    Returns:
        HttpResponse: A rendered HTML response displaying the post's details.

    Raises:
        Http404: If no `Post` object is found with the given primary key.
    """
    post = get_object_or_404(Post, id=pk)

    commentform = CommentCreateForm()
    replyform = ReplyCreateForm()

    if request.htmx:
        if "top" in request.GET:
            comments = (
                post.comments.annotate(likes_count=Count("likes"))
                .filter(likes_count__gt=0)
                .order_by("-likes_count")
            )
        else:
            comments = post.comments.all()
        return render(
            request,
            "snippets/loop_postpage_comments.html",
            {"comments": comments, "replyform": replyform},
        )

    context = {"post": post, "commentform": commentform, "replyform": replyform}

    return render(request, "posts/post_page.html", context)


@login_required
def comment_sent(request: HttpRequest, pk: str) -> HttpResponse:
    """
    Handle the submission of a comment for a specific post.

    Args:
        request (HttpRequest): The HTTP request object containing metadata
        about the request.
        pk (str): The primary key (id) of the post for which the comment is being submitted.

    Returns:
        HttpResponse: A redirect to the post page after successfully adding the comment.

    Raises:
        Http404: If no `Post` object is found with the given primary key.
    """
    post = get_object_or_404(Post, id=pk)
    replyform = ReplyCreateForm()

    if request.method == "POST":
        form = CommentCreateForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.parent_post = post
            comment.save()

    context = {"comment": comment, "post": post, "replyform": replyform}

    return render(request, "snippets/add_comment.html", context)


@login_required
def comment_delete_view(request: HttpRequest, pk: str) -> HttpResponse:
    """
    Handle the deletion of a comment or raise a 404 error if not found.

    Args:
        request (HttpRequest): The HTTP request object containing metadata about the request.
        pk (str): The primary key (id) of the comment to be deleted.

    Returns:
        HttpResponse:
            - A rendered HTML response with the post details for confirmation (GET request).
            - A redirect to the home page upon successful deletion (POST request).

    Raises:
        Http404: If no `Post` object is found with the given primary key.

    Context:
        - `comment`: The post instance to be displayed for confirmation.
    """
    post = get_object_or_404(Comment, id=pk, author=request.user)

    if request.method == "POST":
        post.delete()
        messages.success(request, "Comment deleted")
        return redirect("post", post.parent_post.id)

    return render(request, "posts/comment_delete.html", {"comment": post})


@login_required
def reply_sent(request: HttpRequest, pk: str) -> HttpResponse:
    """
    Handle the submission of a reply for a specific comment.

    Args:
        request (HttpRequest): The HTTP request object containing metadata
        about the request.
        pk (str): The primary key (id) of the post for which the reply is being submitted.

    Returns:
        HttpResponse: A redirect to the post page after successfully adding the reply.

    Raises:
        Http404: If no `Comment` object is found with the given primary key.
    """
    comment = get_object_or_404(Comment, id=pk)
    replyform = ReplyCreateForm()

    if request.method == "POST":
        form = ReplyCreateForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.author = request.user
            reply.parent_comment = comment
            reply.save()

    context = {"comment": comment, "reply": reply, "replyform": replyform}

    return render(request, "snippets/add_reply.html", context)


@login_required
def reply_delete_view(request: HttpRequest, pk: str) -> HttpResponse:
    """
    Handle the deletion of a reply or raise a 404 error if not found.

    Args:
        request (HttpRequest): The HTTP request object containing metadata about the request.
        pk (str): The primary key (id) of the reply to be deleted.

    Returns:
        HttpResponse:
            - A rendered HTML response with the post details for confirmation (GET request).
            - A redirect to the home page upon successful deletion (POST request).

    Raises:
        Http404: If no `Reply` object is found with the given primary key.

    Context:
        - `comment`: The post instance to be displayed for confirmation.
    """
    reply = get_object_or_404(Reply, id=pk, author=request.user)

    if request.method == "POST":
        reply.delete()
        messages.success(request, "Reply deleted")
        return redirect("post", reply.parent_comment.parent_post.id)

    return render(request, "posts/reply_delete.html", {"reply": reply})


def like_toggle(model: type) -> callable:
    """
    A decorator that toggles the like status for a given model instance.

    Args:
        model (type): The model class for which the like functionality is being implemented,
                      e.g., Post, Comment, or Reply.

    Returns:
        callable: A wrapped view function that toggles the like status and calls the original view.
    """

    def inner_func(func: callable) -> callable:
        """
        A wrapper function to perform the like toggle logic.

        Args:
            func (callable): The view function to wrap.

        Returns:
            callable: The wrapped view function.
        """

        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            """
            Toggle the like status for a specific model instance.

            Args:
                request (HttpRequest): The HTTP request object containing user session data.
                *args: Additional positional arguments for the view.
                **kwargs: Keyword arguments, including `pk` to identify the model instance.

            Returns:
                HttpResponse: The response generated by the wrapped view function.
            """
            post = get_object_or_404(model, id=kwargs.get("pk"))
            user_exist = post.likes.filter(username=request.user.username).exists()

            if post.author != request.user:
                if user_exist:
                    post.likes.remove(request.user)
                else:
                    post.likes.add(request.user)

            return func(request, post)

        return wrapper

    return inner_func


@login_required
@like_toggle(Post)
def like_post(request: HttpRequest, post: Post) -> HttpResponse:
    """
    Handle toggling the like status for a blog post.

    Args:
        request (HttpRequest): The HTTP request object containing user session data.
        post (Post): The blog post instance for which the like status is toggled.

    Returns:
        HttpResponse: A rendered HTML snippet displaying the updated like status.
    """
    return render(request, "snippets/likes.html", {"post": post})


@login_required
@like_toggle(Comment)
def like_comment(request: HttpRequest, post: Comment) -> HttpResponse:
    """
    Handle toggling the like status for a comment.

    Args:
        request (HttpRequest): The HTTP request object containing user session data.
        post (Comment): The comment instance for which the like status is toggled.

    Returns:
        HttpResponse: A rendered HTML snippet displaying the updated like status for the comment.
    """
    return render(request, "snippets/likes_comment.html", {"comment": post})


@login_required
@like_toggle(Reply)
def like_reply(request: HttpRequest, post: Reply) -> HttpResponse:
    """
    Handle toggling the like status for a reply.

    Args:
        request (HttpRequest): The HTTP request object containing user session data.
        post (Reply): The reply instance for which the like status is toggled.

    Returns:
        HttpResponse: A rendered HTML snippet displaying the updated like status for the reply.
    """
    return render(request, "snippets/likes_reply.html", {"reply": post})
