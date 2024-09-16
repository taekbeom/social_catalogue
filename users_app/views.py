from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage, send_mail
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from catalogue_app.models import User
from social_catalogue import settings
from .forms import CustomUserCreationForm, CustomLoginForm
from django.contrib.auth import logout as logout_req, login as login_req, authenticate

from .token import generate_token


def login(request):
    if request.method == 'POST':
        form = CustomLoginForm(data=request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            remember_me = request.POST.get("form-remember")
            if not remember_me:
                request.session.set_expiry(0)
            login_req(request, user)
            next = request.GET.get("next", None)
            if next is not None:
                return redirect(next)
            else:
                return redirect('app_home')
    else:
        form = CustomLoginForm()
    content = {
        "title": "Log In",
        "form": form
    }
    return render(request, 'users/login.html', content)


def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            return email_send_confirm(request, user)
    else:
        form = CustomUserCreationForm()
    content = {
        "title": "Sign Up",
        "form": form
    }
    return render(request, 'users/signup.html', content)


def email_send_confirm(request, user):
    current_site = get_current_site(request)
    mail_subject = 'Activation link has been sent to your email id'
    if user.temp_email:
        email = user.temp_email
    else:
        email = user.email
    message = render_to_string('users/email_confirmation.html', {

        'name': user.username,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.id)),
        'token': generate_token.make_token(user),
        'email': email,
    })
    send_mail(mail_subject, message, settings.EMAIL_HOST_USER, [email], fail_silently=True)
    return render(request, 'users/emailactivation.html')


def activate_account(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(id=uid)
    except:
        user = None

    if user is not None and generate_token.check_token(user, token):
        if user.temp_email and not User.objects.filter(email=user.temp_email):
            user.email = user.temp_email
        else:
            user.is_active = True
        user.temp_email = None
        user.save()

        if user is not None:
            login_req(request, user)
            return redirect('app_home')
    else:
        return redirect('app_home')


def logout(request):
    logout_req(request)
    return redirect('app_home')


@login_required
def delete_user_view(request):
    if request.method == 'POST':
        request.user.delete()
        return logout(request)
