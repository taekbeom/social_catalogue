from os.path import basename

import imghdr

from django.contrib.sites.shortcuts import get_current_site
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage, send_mail
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.csrf import csrf_exempt

from catalogue_app.models import Profile, User, Post, Mark, EntryCategory, Feed, Entry
from users_app.forms import UpdateProfileForm, UpdateUserForm
from social_catalogue import settings
from PIL import Image, ImageOps

from users_app.token import generate_token
from users_app.views import email_send_confirm

headers = {'content_type': 'application/json'}


@login_required
def profile(request, profile_id):
    if not Profile.objects.filter(id=profile_id).first():
        return redirect('app_home')
    p_user = User.objects.filter(id=Profile.objects.filter(id=profile_id).first().user_inf.id).first()
    cur_user = request.user.id == p_user.id
    user_dict = {}
    image_is_valid = True
    post_var = None
    post_value_reply = None
    post_display_value_reply = None
    if request.method == 'POST':
        submit_button = request.POST.get('submit-btn')
        if submit_button == 'button-upload':
            post_reply = request.POST.get('post_reply')
            post_display_reply = request.POST.get('post_display_reply')
            image_is_valid = upload_post(request, profile_id, request.POST.get('post_value_upload'),
                                         post_reply, post_display_reply)
            if image_is_valid:
                return redirect('app_profile', profile_id)
        elif submit_button == 'button-edit':
            post_id = request.POST.get('post_value_edit')
            post_var = Post.objects.filter(id=post_id).first()
        else:
            post_value_reply = request.POST.get('post_value_reply')
            post_display_value_reply = request.POST.get('post_value_display_reply')
            if not post_value_reply:
                post_value_reply = post_display_value_reply

    with connection.cursor() as cursor:
        query = "SELECT COUNT(*) FROM notification WHERE profile = %(profile_id)s AND NOT is_read;"
        cursor.execute(query, {"profile_id": profile_id})
        notifications_count = cursor.fetchone()
        if notifications_count:
            notifications_count = notifications_count[0]

        query = """
                SELECT ec.category_name, mark.mark_name, COUNT(le.id) 
                FROM mark
                JOIN profile p ON p.id = mark.profile 
                JOIN list_entry le ON le.mark = mark.id
                JOIN entry e ON e.id = le.entry 
                JOIN entry_type et ON et.id = e.entry_type 
                JOIN entry_category ec ON ec.id = et.entry_category 
                WHERE p.user_inf = %(user_id)s AND mark.is_default 
                GROUP BY mark.id, ec.id
            """
        cursor.execute(query, {"user_id": p_user.id})
        mark_category_counts = cursor.fetchall()

        query = "SELECT mark_name, colour FROM mark WHERE is_default AND profile = %(profile_id)s ORDER BY id ASC"
        cursor.execute(query, {"profile_id": profile_id})
        mark_counts = cursor.fetchall()

        query = "SELECT category_name FROM entry_category"
        cursor.execute(query)
        entry_category_counts = cursor.fetchall()

        query = """
                SELECT message, material, post.add_date, ui.username, ap.picture, ap.id, ui.id, post.id FROM post
                JOIN profile p ON p.id = post.profile
                LEFT JOIN user_inf ui ON ui.id = post.author
                LEFT JOIN profile ap ON ap.user_inf = ui.id
                WHERE p.id = %(profile_id)s AND post.reply_display IS NULL
                ORDER BY post.add_date DESC;
            """
        cursor.execute(query, {"profile_id": profile_id})
        posts = cursor.fetchall()

        query = """
                SELECT message, material, post.add_date, ui.username, ap.picture, ap.id, ui.id, post.id,
                reply, reply_display FROM post
                JOIN profile p ON p.id = post.profile
                LEFT JOIN user_inf ui ON ui.id = post.author
                LEFT JOIN profile ap ON ap.user_inf = ui.id
                WHERE p.id = %(profile_id)s AND post.reply_display IS NOT NULL
                ORDER BY post.id ASC;
            """
        cursor.execute(query, {"profile_id": profile_id})
        posts_reply = cursor.fetchall()

        post_ids = [post[7] for post in posts]
        post_reply_dict = {}
        for post_id in post_ids:
            related_replies = [post_reply for post_reply in posts_reply if post_reply[9] == post_id]
            post_reply_dict[post_id] = related_replies

        if not cur_user:
            query = "SELECT is_visible FROM list_user lu WHERE user1 = %(user1)s AND user2 = %(user2)s;"
            cursor.execute(query, {"user1": request.user.id, "user2": p_user.id})
            user_lists = cursor.fetchall()

            query = "SELECT is_visible FROM list_user lu WHERE user1 = %(user1)s AND user2 = %(user2)s;"
            cursor.execute(query, {"user1": p_user.id, "user2": request.user.id})
            user_lists_out = cursor.fetchall()

            query = """
                SELECT * FROM friend WHERE user1 = %(user1)s AND user2 = %(user2)s OR
                user2 = %(user1)s AND user1 = %(user2)s AND accept;
            """
            cursor.execute(query, {"user1": request.user.id, "user2": p_user.id})
            user_friends = cursor.fetchall()

            query = """
                SELECT * FROM friend WHERE user1 = %(user1)s AND user2 = %(user2)s AND accept OR
                user2 = %(user1)s AND user1 = %(user2)s AND accept;
            """
            cursor.execute(query, {"user1": request.user.id, "user2": p_user.id})
            user_accept_friends = cursor.fetchall()

            user_dict = {"friend": True if user_friends else False,
                            "starred": user_lists[0][0] if user_lists else False,
                            "blocked": not (user_lists[0][0] if user_lists else True),
                            "blocked_out": not (user_lists_out[0][0] if user_lists_out else True),
                            "accept_friend": True if user_accept_friends else False}

        all_mark_category_counts = []

        for mc in mark_counts:
            for ec in entry_category_counts:
                key = (ec[0], mc[0])
                count = next((row[2] for row in mark_category_counts if (row[0], row[1]) == key), 0)
                all_mark_category_counts.append((ec[0], mc[0], count, mc[1]))

    btn_display = display_friend(request.user.id, p_user.id)
    btn_user_display = display_user_list(request.user.id, p_user.id)

    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')

    try:
        posts_page = paginator.page(page_number)
    except PageNotAnInteger:
        posts_page = paginator.page(1)
    except EmptyPage:
        posts_page = paginator.page(paginator.num_pages)

    content = {
        "title": "Profile",
        "posts": posts,
        "posts_page": posts_page,
        "profile_pic": p_user.profile_set.get().picture,
        "lists": all_mark_category_counts,
        "entry_category_counts": entry_category_counts,
        "p_user": p_user,
        "profile_id": profile_id,
        "description": p_user.profile_set.get().description,
        "active": p_user.profile_set.get().active,
        "closed": p_user.profile_set.get().closed,
        "private": p_user.profile_set.get().private,
        "date": p_user.profile_set.get().add_date,
        "cur_user": cur_user,
        "btn_display": btn_display,
        "btn_display_star": btn_user_display["star"] if btn_user_display else "",
        "btn_display_block": btn_user_display["block"] if btn_user_display else "",
        "friend": user_dict["friend"] if user_dict else "",
        "starred": user_dict["starred"] if user_dict else "",
        "blocked": user_dict["blocked"] if user_dict else "",
        "blocked_out": user_dict["blocked_out"] if user_dict else "",
        "accept_friend": user_dict["accept_friend"] if user_dict else "",
        "image_is_valid": image_is_valid,
        "post_var": post_var,
        "posts_replies": post_reply_dict.items(),
        "post_reply": post_value_reply,
        "post_display_reply": post_display_value_reply,
        "notifications_count": notifications_count,
    }
    return render(request, 'profile/profile.html', content)


@login_required
def upload_post(request, profile_id, post_id=None, post_reply=None, post_display_reply=None):
    post_message = request.POST.get('post_message')
    image_is_valid, image_name = upload_image(request, 'upload_image', 'posts')
    if post_id and not image_name:
        material = Post.objects.filter(id=post_id).first().material
        material_check = request.POST.get('material')
        if material_check != material:
            image_name = material_check
        else:
            image_name = '' if material is None else material
    if post_message or image_name:
        with connection.cursor() as cursor:
            if post_id:
                query = """
                        UPDATE post SET message = NULLIF(%(post_message)s, ''), material = NULLIF(%(img)s, '')
                        WHERE id = %(post_id)s and author = %(user_id)s;
                    """
                cursor.execute(query, {"post_message": post_message, "img": basename(image_name),
                                       "post_id": post_id, "user_id": request.user.id})
            else:
                if not post_reply:
                    post_reply = None
                if not post_display_reply:
                    post_display_reply = None
                query = """
                        INSERT INTO post(message, material, profile, author, reply, reply_display)
                        VALUES (NULLIF(%(post_message)s, ''), NULLIF(%(img)s, ''), %(profile_id)s, %(author_id)s,
                        %(post_reply)s, %(post_display_reply)s);
                    """
                cursor.execute(query, {"post_message": post_message, "img": basename(image_name),
                                       "profile_id": profile_id, "author_id": request.user.id,
                                       "post_reply": post_reply, "post_display_reply": post_display_reply})
            connection.commit()
    return image_is_valid


@login_required
def delete_post(request, profile_id):
    if request.method == 'POST':
        post_id = request.POST.get('post_value')
        post = Post.objects.filter(id=post_id).first()
        if post.author == request.user or post.profile == request.user.profile_set.get():
            with connection.cursor() as cursor:
                query = "DELETE FROM post WHERE reply_display = %(post_id)s"
                cursor.execute(query, {"post_id": post_id})
                query = "DELETE FROM post WHERE id = %(post_id)s"
                cursor.execute(query, {"post_id": post_id})
                connection.commit()
    return redirect('app_profile', profile_id)


@login_required
def check_friends(request, profile_id, user1, user2):
    if user1 != user2:
        with connection.cursor() as cursor:
            query = """
                    SELECT user1, accept FROM friend f
                    WHERE user1 = %(user1)s AND user2 = %(user2)s OR user1 = %(user2)s AND user2 = %(user1)s
                """
            cursor.execute(query, {"user1": user1, "user2": user2})
            friendship = cursor.fetchall()
            query = """
                    DELETE FROM list_user WHERE user1 = %(user1)s AND user2 = %(user2)s
                """
            cursor.execute(query, {"user1": user1, "user2": user2})
            if not friendship:
                query = "INSERT INTO friend(user1, user2) VALUES (%(user1)s, %(user2)s)"
                cursor.execute(query, {"user1": user1, "user2": user2})
            elif friendship[0][1]:
                query = """
                        UPDATE friend SET accept = FALSE, user1=%(user2)s, user2=%(user1)s
                        WHERE user1 = %(user1)s AND user2 = %(user2)s OR user1 = %(user2)s AND user2 = %(user1)s
                    """
                cursor.execute(query, {"user1": user1, "user2": user2})
            elif friendship[0][0] != user1:
                query = "UPDATE friend SET accept = TRUE WHERE user1 = %(user2)s AND user2 = %(user1)s"
                cursor.execute(query, {"user1": user1, "user2": user2})
            else:
                query = ("""
                        DELETE FROM friend WHERE user1 = %(user1)s AND user2 = %(user2)s 
                        OR user1 = %(user2)s AND user2 = %(user1)s
                    """)
                cursor.execute(query, {"user1": user1, "user2": user2})
            connection.commit()
    return redirect('app_profile', profile_id)


@login_required
def check_star(request, profile_id, user1, user2):
    if user1 != user2:
        with connection.cursor() as cursor:
            query = """
                    SELECT user1, accept FROM friend f
                    WHERE user1 = %(user1)s AND user2 = %(user2)s OR user1 = %(user2)s AND user2 = %(user1)s
                """
            cursor.execute(query, {"user1": user1, "user2": user2})
            friendship = cursor.fetchall()

            query = "SELECT is_visible FROM list_user WHERE user1 = %(user1)s AND user2 = %(user2)s"
            cursor.execute(query, {"user1": user1, "user2": user2})
            user_option = cursor.fetchall()
            if friendship and friendship[0][1]:
                query = """
                        UPDATE friend SET accept = FALSE, user1=%(user2)s, user2=%(user1)s
                        WHERE user1 = %(user1)s AND user2 = %(user2)s OR user1 = %(user2)s AND user2 = %(user1)s
                    """
                cursor.execute(query, {"user1": user1, "user2": user2})
            elif friendship and friendship[0][0] == user1:
                query = "DELETE FROM friend WHERE user1 = %(user1)s AND user2 = %(user2)s"
                cursor.execute(query, {"user1": user1, "user2": user2})
            if user_option and user_option[0][0]:
                query = "DELETE FROM list_user WHERE user1 = %(user1)s AND user2 = %(user2)s"
                cursor.execute(query, {"user1": user1, "user2": user2})
            elif user_option and not user_option[0][0]:
                query = "UPDATE list_user SET is_visible = TRUE WHERE user1 = %(user1)s AND user2 = %(user2)s"
                cursor.execute(query, {"user1": user1, "user2": user2})
            else:
                query = "INSERT INTO list_user(is_visible, user1, user2) VALUES(TRUE, %(user1)s, %(user2)s)"
                cursor.execute(query, {"user1": user1, "user2": user2})
            connection.commit()
    return redirect('app_profile', profile_id)


@login_required
def check_block(request, profile_id, user1, user2):
    if user1 != user2:
        with connection.cursor() as cursor:
            query = """
                    SELECT user1, accept FROM friend f
                    WHERE user1 = %(user1)s AND user2 = %(user2)s OR user1 = %(user2)s AND user2 = %(user1)s
                """
            cursor.execute(query, {"user1": user1, "user2": user2})
            friendship = cursor.fetchall()

            query = "SELECT is_visible FROM list_user WHERE user1 = %(user1)s AND user2 = %(user2)s"
            cursor.execute(query, {"user1": user1, "user2": user2})
            user_option = cursor.fetchall()
            if friendship and friendship[0][1]:
                query = """
                        UPDATE friend SET accept = FALSE, user1=%(user2)s, user2=%(user1)s
                        WHERE user1 = %(user1)s AND user2 = %(user2)s OR user1 = %(user2)s AND user2 = %(user1)s
                    """
                cursor.execute(query, {"user1": user1, "user2": user2})
            elif friendship and friendship[0][0] == user1:
                query = "DELETE FROM friend WHERE user1 = %(user1)s AND user2 = %(user2)s"
                cursor.execute(query, {"user1": user1, "user2": user2})
            if user_option and user_option[0][0]:
                query = "UPDATE list_user SET is_visible = FALSE WHERE user1 = %(user1)s AND user2 = %(user2)s"
                cursor.execute(query, {"user1": user1, "user2": user2})
            elif user_option and not user_option[0][0]:
                query = "DELETE FROM list_user WHERE user1 = %(user1)s AND user2 = %(user2)s"
                cursor.execute(query, {"user1": user1, "user2": user2})
            else:
                query = "INSERT INTO list_user(is_visible, user1, user2) VALUES(FALSE, %(user1)s, %(user2)s)"
                cursor.execute(query, {"user1": user1, "user2": user2})
            connection.commit()
    return redirect('app_profile', profile_id)


def display_friend(user1, user2):
    if user1 != user2:
        with connection.cursor() as cursor:
            query = """
                    SELECT user1, accept FROM friend f
                    WHERE user1 = %(user1)s AND user2 = %(user2)s OR user1 = %(user2)s AND user2 = %(user1)s
                """
            cursor.execute(query, {"user1": user1, "user2": user2})
            friendship = cursor.fetchall()
            if not friendship:
                return "fa-user-plus", "btn-dark"
            elif friendship[0] and friendship[0][1]:
                return "fa-user-minus", "btn-success"
            elif friendship[0] and friendship[0][0] != user1:
                return "fa-user-plus", "btn-warning"
            else:
                return "fa-user-minus", "btn-secondary"


def display_user_list(user1, user2):
    if user1 != user2:
        with connection.cursor() as cursor:
            query = "SELECT is_visible FROM list_user WHERE user1 = %(user1)s AND user2 = %(user2)s"
            cursor.execute(query, {"user1": user1, "user2": user2})
            user_in_list = cursor.fetchall()
            if not user_in_list:
                return {"star": "btn-warning", "block": "btn-danger"}
            elif user_in_list[0][0]:
                return {"star": "btn-success", "block": "btn-danger"}
            else:
                return {"star": "btn-warning", "block": "btn-secondary"}


@login_required
def edit_profile(request, profile_id):
    user_profile = get_object_or_404(Profile, id=profile_id)

    if user_profile.user_inf == request.user:
        image_is_valid = True
        if request.method == 'POST':
            u_form = UpdateUserForm(user=request.user, data=request.POST, instance=request.user)
            p_form = UpdateProfileForm(request.POST, instance=Profile.objects.filter(id=profile_id).first())

            if u_form.is_valid() and p_form.is_valid():
                u_form.request = request
                user = u_form.save()
                if request.user.temp_email:
                    return email_send_confirm(request, user)
                p_form.save()
                image_is_valid, image_name = upload_image(request, 'edit_image_input', 'profile_pics', True)
                if image_name:
                    Profile.objects.filter(id=profile_id).update(picture=basename(image_name))
                if image_is_valid:
                    return redirect('app_profile', profile_id)
        else:
            u_form = UpdateUserForm(user=request.user, instance=request.user)
            p_form = UpdateProfileForm(instance=Profile.objects.filter(id=profile_id).first())

        content = {
            "title": "Edit Profile",
            "u_form": u_form,
            "p_form": p_form,
            "profile": Profile.objects.filter(id=profile_id).first(),
            "image_is_valid": image_is_valid,
        }
        return render(request, 'profile/edit.html', content)
    else:
        return redirect('app_profile', profile_id=profile_id)


def validate_image(image):
    extension = image.name.split('.')[-1]
    if not extension or extension.lower() not in settings.WHITELISTED_IMAGE_TYPES.keys():
        return False
    content_type = image.content_type
    if content_type not in settings.WHITELISTED_IMAGE_TYPES.values():
        return False
    image_type = imghdr.what(None, h=image.read(32))
    if image_type not in settings.WHITELISTED_IMAGE_TYPES:
        return False
    return True


def upload_image(request, image_url, folder, resize=False):
    if image_url in request.FILES:
        image = request.FILES[image_url]
        image_is_valid = validate_image(image)
        if image_is_valid:
            image_name = default_storage.save(f'{folder}/{image.name}', image)
            if resize:
                img_path = settings.MEDIA_URL + folder + '/' + basename(image_name)
                img = Image.open(img_path)
                if img.height > 300 or img.width > 300:
                    img = ImageOps.fit(img, (300, 300))
                img.save(img_path)
            return True, image_name
        else:
            return False, ''
    return True, ''


@login_required
def chat(request, profile_id):
    user_profile = get_object_or_404(Profile, id=profile_id)

    if user_profile.user_inf == request.user:
        return render(request, 'profile/chat.html')
    else:
        return redirect('app_profile', profile_id=profile_id)


@login_required
def feed(request, profile_id):
    user_profile = get_object_or_404(Profile, id=profile_id)

    if user_profile.user_inf == request.user:
        feed_page = None
        with connection.cursor() as cursor:
            query = """
                    SELECT message, feed.add_date, e.id, e.title, p.id, ui.username FROM feed
                    JOIN profile p ON p.user_inf = feed.user_inf
                    JOIN user_inf ui ON ui.id = p.user_inf
                    JOIN entry e ON e.id = feed.entry
                    WHERE feed.profile = %(profile_id)s AND feed.user_inf != %(user_id)s
                    ORDER BY add_date DESC
                """
            cursor.execute(query, {"profile_id": profile_id, "user_id": request.user.id})
            feed_list = cursor.fetchall()

        if feed_list:
            paginator = Paginator(feed_list, 10)
            page_number = request.GET.get('page')

            try:
                feed_page = paginator.page(page_number)
            except PageNotAnInteger:
                feed_page = paginator.page(1)
            except EmptyPage:
                feed_page = paginator.page(paginator.num_pages)

        content = {
            "title": "Feed",
            "feed_page": feed_page,
        }
        return render(request, 'profile/feed.html', content)
    else:
        return redirect('app_profile', profile_id=profile_id)


@login_required
def friend_list(request, profile_id):
    p_user = User.objects.filter(id=Profile.objects.filter(id=profile_id).first().user_inf.id).first()
    user_list = request.GET.get("user_list", "friends")
    if request.user.id != p_user.id:
        user_list = "friends"
    if user_list == "block_list":
        users, title = blocklist(profile_id)
    elif user_list == "requests":
        users, title = requests(profile_id)
    elif user_list == "out_requests":
        users, title = out_requests(profile_id)
    elif user_list == "following":
        users, title = following(profile_id)
    else:
        users, title = friends(profile_id)
    content = {
        "title": title,
        "users": users,
        "profile_id": profile_id,
        "user_list": user_list,
        "cur_user": request.user.id == p_user.id,
        "active": p_user.profile_set.get().active,
        "private": p_user.profile_set.get().private,
    }
    return render(request, 'profile/friendlist.html', content)


def friends(profile_id):
    p_user = User.objects.filter(id=Profile.objects.filter(id=profile_id).first().user_inf.id).first()
    with connection.cursor() as cursor:
        query = """
                SELECT ui.username, p.picture, p.id, f.add_date FROM friend f
                JOIN user_inf ui ON ui.id = f.user1
                JOIN profile p ON p.user_inf = ui.id
                WHERE user2 = %(user_id)s and accept
                UNION
                SELECT ui.username, p.picture, p.id, f.add_date FROM friend f
                JOIN user_inf ui ON ui.id = f.user2
                JOIN profile p ON p.user_inf = ui.id
                WHERE user1 = %(user_id)s and accept;
            """
        cursor.execute(query, {"user_id": p_user.id})
        users = cursor.fetchall()
    return users, "Friends"


def requests(profile_id):
    p_user = User.objects.filter(id=Profile.objects.filter(id=profile_id).first().user_inf.id).first()
    with connection.cursor() as cursor:
        query = """
                SELECT ui.username, p.picture, p.id FROM friend f
                JOIN user_inf ui ON ui.id = f.user1
                JOIN profile p ON p.user_inf = ui.id
                WHERE user2 = %(user_id)s and accept = FALSE
            """
        cursor.execute(query, {"user_id": p_user.id})
        users = cursor.fetchall()
    return users, "Requests"


def out_requests(profile_id):
    p_user = User.objects.filter(id=Profile.objects.filter(id=profile_id).first().user_inf.id).first()
    with connection.cursor() as cursor:
        query = """
                SELECT ui.username, p.picture, p.id FROM friend f
                JOIN user_inf ui ON ui.id = f.user2
                JOIN profile p ON p.user_inf = ui.id
                WHERE user1 = %(user_id)s and accept = FALSE;
            """
        cursor.execute(query, {"user_id": p_user.id})
        users = cursor.fetchall()
    return users, "Outgoing Requests"


def following(profile_id):
    p_user = User.objects.filter(id=Profile.objects.filter(id=profile_id).first().user_inf.id).first()
    with connection.cursor() as cursor:
        query = """
                SELECT ui.username, p.picture, p.id FROM list_user lu
                JOIN user_inf ui ON ui.id = lu.user2
                JOIN profile p ON p.user_inf = ui.id
                WHERE user1 = %(user_id)s and is_visible
            """
        cursor.execute(query, {"user_id": p_user.id})
        users = cursor.fetchall()
    return users, "Following"


def blocklist(profile_id):
    p_user = User.objects.filter(id=Profile.objects.filter(id=profile_id).first().user_inf.id).first()
    with connection.cursor() as cursor:
        query = """
                SELECT ui.username, p.picture, p.id FROM list_user lu
                JOIN user_inf ui ON ui.id = lu.user2
                JOIN profile p ON p.user_inf = ui.id
                WHERE user1 = %(user_id)s and is_visible = FALSE
            """
        cursor.execute(query, {"user_id": p_user.id})
        users = cursor.fetchall()
    return users, "Block list"


@login_required
def history(request, profile_id):
    user_profile = get_object_or_404(Profile, id=profile_id)

    if user_profile.user_inf == request.user:
        feed_page = None
        with connection.cursor() as cursor:
            query = """
                    SELECT message, feed.add_date, e.id, e.title, p.id, ui.username FROM feed
                    JOIN profile p ON p.user_inf = feed.user_inf
                    JOIN user_inf ui ON ui.id = p.user_inf
                    JOIN entry e ON e.id = feed.entry
                    WHERE feed.profile = %(profile_id)s AND feed.user_inf = %(user_id)s
                    ORDER BY add_date DESC
                """
            cursor.execute(query, {"profile_id": profile_id, "user_id": request.user.id})
            feed_list = cursor.fetchall()

        if feed_list:
            paginator = Paginator(feed_list, 10)
            page_number = request.GET.get('page')

            try:
                feed_page = paginator.page(page_number)
            except PageNotAnInteger:
                feed_page = paginator.page(1)
            except EmptyPage:
                feed_page = paginator.page(paginator.num_pages)

        content = {
            "title": "History",
            "feed_page": feed_page,
        }
        return render(request, 'profile/history.html', content)
    else:
        return redirect('app_profile', profile_id=profile_id)


@login_required
def notifications(request, profile_id):
    user_profile = get_object_or_404(Profile, id=profile_id)

    if user_profile.user_inf == request.user:
        notify_page = None
        colour_list = {1: ["#1B2A63", "#9BD5ED"], 2: ["#67722F", "#EAF7A6"],
                       3: ["#1B6320", "#9BEFA1"], 4: ["#663C1A", "#FAB4A3"],
                       6: ["#252525", "#CEC9C9"]}
        with connection.cursor() as cursor:
            query = """
                    SELECT nc.category_name, message, p.id, ui.username, ne.entry, e.title, is_read, nc.id, n.id,
                    e.confirmed FROM notification n
                    JOIN notification_category nc ON nc.id = n.notification_category
                    LEFT JOIN notification_user nu ON nu.notification = n.id
                    LEFT JOIN profile p ON p.user_inf = nu.user_inf
                    LEFT JOIN user_inf ui ON ui.id = p.user_inf
                    LEFT JOIN notification_entry ne ON ne.notification = n.id
                    LEFT JOIN entry e ON e.id = ne.entry
                    WHERE n.profile = %(profile_id)s
                    ORDER BY n.id DESC;
                """
            cursor.execute(query, {"profile_id": profile_id})
            notify_list = cursor.fetchall()

        if notify_list:
            paginator = Paginator(notify_list, 10)
            page_number = request.GET.get('page')

            try:
                notify_page = paginator.page(page_number)
            except PageNotAnInteger:
                notify_page = paginator.page(1)
            except EmptyPage:
                notify_page = paginator.page(paginator.num_pages)

        content = {
            "title": "Notifications",
            "notify_page": notify_page,
            "colour_list": colour_list.items(),
            "profile_id": profile_id,
        }
        return render(request, 'profile/notification.html', content)
    else:
        return redirect('app_profile', profile_id=profile_id)


@csrf_exempt
def mark_notifications_as_read(request, profile_id):
    if request.method == 'POST':
        notification_ids = request.POST.getlist('notification_ids[]')
        if notification_ids:
            with connection.cursor() as cursor:
                notification_string = notification_ids[0]
                notification_list = notification_string.split(",")
                for n in notification_list:
                    query = "UPDATE notification SET is_read = TRUE WHERE id = %(n)s;"
                    cursor.execute(query, {"n": int(n)})
                    connection.commit()
    return redirect('app_notifications', profile_id=profile_id)


@login_required
def catalogue_lists(request, profile_id):
    p_user = User.objects.filter(id=Profile.objects.filter(id=profile_id).first().user_inf.id).first()
    cur_user = request.user.id == p_user.id
    mark_id = request.GET.get('mark_id')
    category = request.GET.get('category-select')
    mark_name = None
    mark_colour = None
    categories = None
    entry_lists = None
    mark_vals = None
    category_name = None
    with connection.cursor() as cursor:
        query = "SELECT id, mark_name FROM mark WHERE profile = %(profile_id)s ORDER BY id;"
        cursor.execute(query, {"profile_id": profile_id})
        marks = cursor.fetchall()

        if mark_id:
            query = "SELECT mark_name, colour FROM mark WHERE profile = %(profile_id)s AND id = %(mark_id)s;"
            cursor.execute(query, {"profile_id": profile_id, "mark_id": mark_id})
            mark_vals = cursor.fetchone()
        if mark_vals:
            mark_name = mark_vals[0]
            mark_colour = mark_vals[1]

            query = """
                    SELECT DISTINCT ec.id, ec.category_name FROM mark m
                    JOIN list_entry le ON m.id = le.mark
                    JOIN entry e ON e.id = le.entry
                    JOIN entry_type et ON et.id = e.entry_type
                    JOIN entry_category ec ON ec.id = et.entry_category
                    WHERE profile = %(profile_id)s AND m.id = %(mark_id)s;
                """
            cursor.execute(query, {"profile_id": profile_id, "mark_id": mark_id})
            categories = cursor.fetchall()
            if not category and categories:
                category = categories[0][0]

        if categories:
            query = """
                    SELECT DISTINCT ON (e.id, le.add_date) e.id, e.title, le.rate, le.add_date, m2.is_default
                    FROM mark m JOIN list_entry le ON m.id = le.mark
                    JOIN entry e ON e.id = le.entry
                    JOIN entry_type et ON et.id = e.entry_type
                    JOIN entry_category ec ON ec.id = et.entry_category
                    LEFT JOIN list_entry le2 ON le2.entry = e.id
                    LEFT JOIN mark m2 ON le2.mark = m2.id AND m2.profile = %(request_profile)s
                    WHERE m.profile = %(profile_id)s AND m.id = %(mark_id)s AND ec.id = %(category)s
                    ORDER BY le.add_date DESC, e.id, m2.is_default DESC NULLS LAST;
                """

            cursor.execute(query, {"profile_id": profile_id, "mark_id": mark_id, "category": category,
                                   "request_profile": request.user.profile_set.get().id})
            entry_lists = cursor.fetchall()

    if category:
        category_name = EntryCategory.objects.filter(id=category).first().category_name
        category = int(category)

    content = {
        "title": "Catalogue Lists",
        "profile_id": profile_id,
        "marks": marks,
        "mark_id": mark_id,
        "mark_name": mark_name,
        "categories": categories,
        "mark_colour": mark_colour,
        "entry_lists": entry_lists,
        "category": category,
        "category_name": category_name,
        "cur_user": cur_user,
    }
    return render(request, 'profile/entrylists.html', content)


@login_required
def add_mark(request, profile_id):
    p_user = User.objects.filter(id=Profile.objects.filter(id=profile_id).first().user_inf.id).first()
    cur_user = request.user.id == p_user.id
    if cur_user:
        if request.method == 'POST':
            list_name = request.POST.get('new-list')
            list_colour = request.POST.get('list-colour')
            mark = Mark.objects.filter(mark_name=list_name, profile=profile_id).first()
            if list_name and not mark:
                with connection.cursor() as cursor:
                    query = """
                            INSERT INTO mark(mark_name, colour, profile)
                            VALUES(%(list_name)s, %(list_colour)s, %(profile_id)s);
                        """
                    cursor.execute(query, {"list_name": list_name, "list_colour": list_colour, "profile_id": profile_id})
                    connection.commit()
    return redirect('app_lists', profile_id)


@login_required
def delete_mark(request, profile_id):
    p_user = User.objects.filter(id=Profile.objects.filter(id=profile_id).first().user_inf.id).first()
    cur_user = request.user.id == p_user.id
    if cur_user:
        if request.method == 'POST':
            mark_id = request.POST.get('mark_id')
            if mark_id and mark_id != 'None':
                with connection.cursor() as cursor:
                    query = """
                            SELECT 1 FROM MARK WHERE id=%(mark_id)s AND profile=%(profile_id)s AND NOT is_default;
                        """
                    cursor.execute(query, {"mark_id": mark_id, "profile_id": profile_id})
                    mark = cursor.fetchall()
                    if mark:
                        query = """
                                DELETE FROM MARK WHERE id=%(mark_id)s AND profile=%(profile_id)s;
                            """
                        cursor.execute(query, {"mark_id": mark_id, "profile_id": profile_id})
                        connection.commit()
    return redirect('app_lists', profile_id)
