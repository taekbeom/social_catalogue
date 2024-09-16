from django.db import models
from django.contrib.auth.models import (Group, Permission, AbstractUser, BaseUserManager, PermissionsMixin)


class UserRole(models.Model):
    id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=16)

    class Meta:
        db_table = 'user_role'


class UserManager(BaseUserManager):
    def create_user(self, username, email, password, user_role, **extra_fields):
        if not username:
            raise ValueError('The User Name must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, user_role=user_role, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, email, password, user_role=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username=username, email=email, password=password, user_role=user_role, **extra_fields)


class User(AbstractUser, PermissionsMixin):
    id = models.AutoField(primary_key=True)
    user_role = models.ForeignKey(UserRole, db_column="user_role", null=True, on_delete=models.SET_NULL)
    temp_email = models.CharField(db_column="temp_email", null=True)
    recommendations = models.BooleanField()
    group = models.ForeignKey(Group, on_delete=models.CASCADE, default=1, related_name='user_set_group')
    groups = models.ManyToManyField(Group, blank=True, related_name='users')
    user_permissions = models.ManyToManyField(Permission, blank=True, related_name='users',
                                              verbose_name='user permissions')
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    objects = UserManager()

    class Meta:
        db_table = 'user_inf'

    def __str__(self):
        return self.username

    @classmethod
    def get_entry_count(cls):
        query = '''
                SELECT  * FROM news ORDER BY add_date DESC LIMIT 9
            '''
        return cls.objects.raw(query)


class Profile(models.Model):
    id = models.AutoField(primary_key=True)
    picture = models.TextField()
    description = models.TextField()
    add_date = models.DateTimeField()  # change
    closed = models.BooleanField()
    private = models.BooleanField()
    active = models.BooleanField()
    user_inf = models.ForeignKey(User, db_column="user_inf", on_delete=models.CASCADE)

    class Meta:
        db_table = 'profile'


class News(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.TextField()
    message = models.TextField()
    image = models.TextField()
    add_date = models.DateTimeField()
    author = models.ForeignKey(User, db_column="author", null=True, on_delete=models.SET_NULL)

    @classmethod
    def get_top_news(cls):
        query = '''
                SELECT * FROM news ORDER BY add_date DESC LIMIT 5
            '''
        return cls.objects.raw(query)

    @classmethod
    def get_rest_news(cls):
        query = '''
                SELECT * FROM news ORDER BY add_date DESC OFFSET 5
            '''
        return cls.objects.raw(query)

    class Meta:
        db_table = 'news'


class Post(models.Model):
    id = models.AutoField(primary_key=True)
    message = models.TextField()
    material = models.TextField()
    add_date = models.DateTimeField()  # change
    profile = models.ForeignKey(Profile, db_column="profile", on_delete=models.CASCADE)
    author = models.ForeignKey(User, db_column="author", null=True, on_delete=models.SET_NULL)
    reply = models.ForeignKey('self', related_name='replies', db_column="reply", null=True, on_delete=models.SET_NULL)
    reply_display = models.ForeignKey('self', related_name='replies_display', db_column="reply_display", on_delete=models.CASCADE)

    class Meta:
        db_table = 'post'


class Friend(models.Model):
    id = models.AutoField(primary_key=True)
    add_date = models.DateTimeField()  # change
    accept = models.BooleanField()
    user1 = models.ForeignKey(User, related_name='user1', db_column='user1', on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name='user2', db_column='user2', on_delete=models.CASCADE)

    class Meta:
        db_table = 'friend'


class ListUser(models.Model):
    id = models.AutoField(primary_key=True)
    is_visible = models.BooleanField()
    user1 = models.ForeignKey(User, related_name='user1_list', db_column='user1', on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name='user2_list', db_column='user2', on_delete=models.CASCADE)

    class Meta:
        db_table = 'list_user'


class Chat(models.Model):  # write a function if all participants are not present chat is deleted
    id = models.AutoField(primary_key=True)
    chat_name = models.CharField(max_length=128)

    class Meta:
        db_table = 'chat'


class ChatParticipant(models.Model):
    id = models.AutoField(primary_key=True)
    chat = models.ForeignKey(Chat, db_column="chat", on_delete=models.CASCADE)
    user_inf = models.ForeignKey(User, db_column="user_inf", null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'chat_participant'


class Message(models.Model):
    id = models.AutoField(primary_key=True)
    message_text = models.TextField()
    material = models.TextField()
    add_date = models.DateTimeField()  # change
    author = models.ForeignKey(ChatParticipant, db_column="author", null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'message'


class NotificationCategory(models.Model):
    id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=32)

    class Meta:
        db_table = 'notification_category'


class Notification(models.Model):
    id = models.AutoField(primary_key=True)
    message = models.TextField()
    is_read = models.BooleanField()
    profile = models.ForeignKey(Profile, db_column="profile", on_delete=models.CASCADE)
    notification_category = models.ForeignKey(NotificationCategory,
                                              db_column="notification_category", null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'notification'


class Mark(models.Model):
    id = models.AutoField(primary_key=True)
    mark_name = models.CharField(max_length=128)
    colour = models.CharField(max_length=7)
    is_default = models.BooleanField()
    profile = models.ForeignKey(Profile, db_column="profile", on_delete=models.CASCADE)

    class Meta:
        db_table = 'mark'


class EntryCategory(models.Model):
    id = models.AutoField(primary_key=True)
    category_name = models.CharField(32)

    class Meta:
        db_table = 'entry_category'


class EntryType(models.Model):
    id = models.AutoField(primary_key=True)
    type_name = models.CharField(max_length=32)
    entry_category = models.ForeignKey(EntryCategory, db_column="entry_category", on_delete=models.CASCADE)

    class Meta:
        db_table = 'entry_type'


class Tag(models.Model):
    id = models.AutoField(primary_key=True)
    tag_name = models.CharField(max_length=32)

    class Meta:
        db_table = 'tag'


class AuthorInf(models.Model):
    id = models.AutoField(primary_key=True)
    author_name = models.CharField(max_length=128)
    picture = models.TextField()
    confirmed = models.BooleanField()

    class Meta:
        db_table = 'author_inf'


class Franchise(models.Model):
    id = models.AutoField(primary_key=True)
    franchise_name = models.CharField(max_length=128)
    confirmed = models.BooleanField()

    class Meta:
        db_table = 'franchise'


class Entry(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=128)
    alt_title = models.TextField()
    add_date = models.DateField()  # change
    plan_date = models.IntegerField()
    cover_img = models.TextField()
    fin_date = models.DateField()  # change
    cur_parts = models.IntegerField()
    total_parts = models.IntegerField()
    description = models.TextField()
    country = models.CharField(max_length=128)
    production = models.CharField(max_length=64)
    entry_type = models.ForeignKey(EntryType, db_column="entry_type", null=True, on_delete=models.SET_NULL)
    franchise = models.ForeignKey(Franchise, db_column="franchise", null=True, on_delete=models.SET_NULL)
    confirmed = models.BooleanField()

    class Meta:
        db_table = 'entry'


class NotificationUser(models.Model):
    user = models.ForeignKey(User, db_column="user_inf", on_delete=models.CASCADE)
    notification = models.ForeignKey(Notification, db_column="notification", on_delete=models.CASCADE)

    class Meta:
        db_table = 'notification_user'


class NotificationEntry(models.Model):
    entry = models.ForeignKey(Entry, db_column="entry", on_delete=models.CASCADE)
    notification = models.ForeignKey(Notification, db_column="notification", on_delete=models.CASCADE)

    class Meta:
        db_table = 'notification_entry'


class Feed(models.Model):
    id = models.AutoField(primary_key=True)
    message = models.TextField()
    add_date = models.DateTimeField()
    profile = models.ForeignKey(Profile, db_column="profile", on_delete=models.CASCADE)
    user_inf = models.ForeignKey(User, db_column="user_inf", null=True, on_delete=models.SET_NULL)
    entry = models.ForeignKey(Entry, db_column="entry", on_delete=models.CASCADE)

    class Meta:
        db_table = 'feed'


class EntryUser(models.Model):
    user_inf = models.ForeignKey(User, db_column="user_inf", null=True, on_delete=models.SET_NULL)
    entry = models.ForeignKey(Entry, db_column="entry", on_delete=models.CASCADE)
    add_date = models.DateTimeField()

    class Meta:
        db_table = 'entry_user'


class EntryTag(models.Model):
    tag = models.ForeignKey(Tag, db_column="tag", on_delete=models.CASCADE)
    entry = models.ForeignKey(Entry, db_column="entry", on_delete=models.CASCADE)

    class Meta:
        db_table = 'entry_tag'


class EntryAuthor(models.Model):
    id = models.AutoField(primary_key=True)
    author = models.ForeignKey(AuthorInf, db_column="author", on_delete=models.CASCADE)
    entry = models.ForeignKey(Entry, db_column="entry", on_delete=models.CASCADE)
    author_role = models.TextField()

    class Meta:
        db_table = 'entry_author'


class Review(models.Model):
    id = models.AutoField(primary_key=True)
    message = models.TextField()
    add_date = models.DateTimeField()  # change
    entry = models.ForeignKey(Entry, db_column="entry", on_delete=models.CASCADE)
    author = models.ForeignKey(User, db_column="author", null=True, on_delete=models.SET_NULL)
    reply = models.ForeignKey('self', related_name='replies', db_column="reply", null=True, on_delete=models.SET_NULL)
    reply_display = models.ForeignKey('self', related_name='replies_display', db_column="reply_display",
                                      on_delete=models.CASCADE)

    class Meta:
        db_table = 'review'


class ListEntry(models.Model):
    id = models.AutoField(primary_key=True)
    add_date = models.DateField()  # change
    rate = models.IntegerField()
    entry = models.ForeignKey(Entry, db_column="entry", on_delete=models.CASCADE)
    mark = models.ForeignKey(Mark, db_column="mark", on_delete=models.CASCADE)

    class Meta:
        db_table = 'list_entry'
