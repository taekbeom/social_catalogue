from django.db import models


class UserRole(models.Model):
    role_id = models.IntegerField(primary_key=True)
    role_name = models.CharField(max_length=16)

    class Meta:
        db_table = 'user_role'


class User(models.Model):
    user_id = models.IntegerField(primary_key=True)
    user_name = models.CharField(max_length=128)
    user_pswd = models.CharField(max_length=64)
    role = models.ForeignKey(UserRole, null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'user_inf'


class Profile(models.Model):
    profile_id = models.IntegerField(primary_key=True)
    profile_pic = models.TextField()
    profile_desc = models.TextField()
    profile_date = models.DateField()  # change
    profile_active = models.BooleanField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = 'profile'


class Post(models.Model):
    post_id = models.IntegerField(primary_key=True)
    post_message = models.TextField()
    post_material = models.TextField()
    post_like = models.IntegerField()
    post_date = models.DateTimeField()  # change
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    reply = models.ForeignKey('self', on_delete=models.CASCADE)

    class Meta:
        db_table = 'post'


class ProfileFeed(models.Model):
    feed_id = models.IntegerField(primary_key=True)
    feed_text = models.TextField()
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)

    class Meta:
        db_table = 'profile_feed'


class News(models.Model):
    news_id = models.IntegerField(primary_key=True)
    news_title = models.TextField()
    news_message = models.TextField()
    news_image = models.TextField()
    news_date = models.DateTimeField()
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'news'


class Friend(models.Model):
    friend_id = models.IntegerField(primary_key=True)
    friend_date = models.DateField()  # change
    user1 = models.ForeignKey(User, related_name='user1', db_column='user1_id', on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name='user2', db_column='user2_id', on_delete=models.CASCADE)

    class Meta:
        db_table = 'friend'


class ChatRoom(models.Model):  # write a function if all participants are not present chat is deleted
    chat_id = models.IntegerField(primary_key=True)
    chat_name = models.CharField(max_length=128)

    class Meta:
        db_table = 'chat_room'


class ChatParticipant(models.Model):
    participant_id = models.IntegerField(primary_key=True)
    chat = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'chat_participant'


class DirectMessage(models.Model):
    message_id = models.IntegerField(primary_key=True)
    message_text = models.TextField()
    message_material = models.TextField()
    message_date = models.DateTimeField()  # change
    message_author = models.ForeignKey(ChatParticipant, on_delete=models.CASCADE)

    class Meta:
        db_table = 'direct_message'


class NotificationCategory(models.Model):
    category_id = models.IntegerField(primary_key=True)
    category_tag = models.CharField(max_length=32)

    class Meta:
        db_table = 'notification_category'


class Notification(models.Model):
    notif_id = models.IntegerField(primary_key=True)
    notif_message = models.TextField()
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    category = models.ForeignKey(NotificationCategory, null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'notification'


class Mark(models.Model):
    mark_id = models.IntegerField(primary_key=True)
    mark_name = models.CharField(max_length=128, unique=True)
    mark_colour = models.CharField(max_length=7)

    class Meta:
        db_table = 'mark'


class EntryCategory(models.Model):
    category_id = models.IntegerField(primary_key=True)
    category_name = models.CharField(32)

    class Meta:
        db_table = 'entry_category'


class EntryType(models.Model):
    type_id = models.IntegerField(primary_key=True)
    type_name = models.CharField(max_length=32)

    class Meta:
        db_table = 'entry_type'


class EntryTag(models.Model):
    tag_id = models.IntegerField(primary_key=True)
    tag_name = models.CharField(max_length=32)

    class Meta:
        db_table = 'entry_tag'


class CatalogueEntry(models.Model):
    entry_id = models.IntegerField(primary_key=True)
    entry_title = models.CharField(max_length=128)
    entry_alt_title = models.TextField()
    entry_release = models.DateTimeField()  # change
    entry_fin = models.DateTimeField()  # change
    entry_author = models.TextField()
    entry_description = models.TextField()
    entry_category = models.ForeignKey(EntryCategory, null=True, on_delete=models.SET_NULL)
    entry_type = models.ForeignKey(EntryType, null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'catalogue_entry'


class Review(models.Model):
    review_id = models.IntegerField(primary_key=True)
    review_message = models.TextField()
    review_date = models.DateTimeField()  # change
    entry = models.ForeignKey(CatalogueEntry, on_delete=models.CASCADE)
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    reply = models.ForeignKey('self', on_delete=models.CASCADE)

    class Meta:
        db_table = 'review'


class CatalogueEntryTag(models.Model):
    tag = models.ForeignKey(EntryTag, on_delete=models.CASCADE)
    entry = models.ForeignKey(CatalogueEntry, on_delete=models.CASCADE)

    class Meta:
        db_table = 'catalogue_entry_tag'


class ListItem(models.Model):
    item_id = models.IntegerField(primary_key=True)
    item_date = models.DateTimeField()  # change
    item_rate = models.IntegerField()
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    entry = models.ForeignKey(CatalogueEntry, on_delete=models.CASCADE)
    mark = models.ForeignKey(Mark, on_delete=models.CASCADE)

    class Meta:
        db_table = 'list_item'
