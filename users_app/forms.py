from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q


from catalogue_app.models import User, UserRole, Profile
from django.contrib.auth import authenticate, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm, UserModel


class CustomUserCreationForm(forms.ModelForm):

    password2 = forms.CharField(label='Password2', widget=forms.PasswordInput, min_length=6)

    class Meta:
        model = User
        fields = ["username", "email", "password", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].required = False
        self.fields['email'].required = False
        self.fields['password'].required = False
        self.fields['password2'].required = False

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if not username:
            raise ValidationError("Please enter your username.")
        elif len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")
        elif len(username) > 128:
            raise ValidationError("Username must be at most 128 characters long.")
        elif User.objects.filter(username=username).exists():
            raise ValidationError("Username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if not email:
            raise ValidationError("Please enter your email.")
        elif User.objects.filter(email=email).exists():
            raise ValidationError("Email already exists.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError("Invalid email address.")
        return email

    def clean_password(self):
        password1 = self.cleaned_data['password']
        if not password1:
            raise ValidationError("Please enter your password.")
        elif len(password1) < 6:
            raise ValidationError("Password must be at least 6 characters long.")
        return password1

    def clean_password2(self):
        password1 = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = User(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            user_role=UserRole.objects.get(id=3)
        )
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class CustomLoginForm(AuthenticationForm):
    error_messages = {
        'invalid_login': "Invalid username or password.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].required = False
        self.fields['password'].required = False

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError('Please enter your username.')
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not password:
            raise ValidationError('Please enter your password.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            cleaned_data['user'] = user
            if user is None:
                raise ValidationError("Invalid username or password.")

        return cleaned_data


class UpdateUserForm(forms.ModelForm):
    password = forms.CharField(label='Password', widget=forms.PasswordInput, min_length=6, required=False)
    password2 = forms.CharField(label='Password2', widget=forms.PasswordInput, min_length=6, required=False)
    new_email = forms.EmailField(label='New Email', required=False)

    class Meta:
        model = User
        fields = ["username", "new_email"]

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].required = False
        self.fields['new_email'].required = False
        self.user = user

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")
        elif len(username) > 128:
            raise ValidationError("Username must be at most 128 characters long.")
        elif User.objects.filter(~Q(id=self.user.id), username=username).exists():
            raise ValidationError("Username already exists.")
        return username

    def clean_new_email(self):
        email = self.cleaned_data['new_email'].strip()
        if User.objects.filter(~Q(id=self.user.id), email=email).exists():
            raise ValidationError("Email already exists.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError("Invalid email address.")
        return email

    def clean_password(self):
        password1 = self.cleaned_data['password']
        if password1 and len(password1) < 6:
            raise ValidationError("Password must be at least 6 characters long.")
        return password1

    def clean_password2(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        username = self.cleaned_data.get('username')
        email = self.cleaned_data.get('new_email')
        if commit:
            if username:
                user.username = username
            if email and email != user.email:
                user.temp_email = email
            user.save()
            update_session_auth_hash(self.request, user)
        return user


class UpdateProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["description", "active", "private", "closed"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['active'].required = False
        self.fields['private'].required = False
        self.fields['closed'].required = False

    def clean(self):
        cleaned_data = super().clean()
        form_delete = self.cleaned_data.get('active')
        form_private = self.cleaned_data.get('private')
        form_closed = self.cleaned_data.get('closed')

        if form_delete:
            cleaned_data['active'] = False
        else:
            cleaned_data['active'] = True

        if form_private:
            cleaned_data['private'] = True
        else:
            cleaned_data['private'] = False

        if form_closed:
            cleaned_data['closed'] = True
        else:
            cleaned_data['closed'] = False

        return cleaned_data
