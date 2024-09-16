from collections import defaultdict
from datetime import datetime
from os.path import basename

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render, redirect
from django.utils.dateparse import parse_date

from .forms import NewsCreationForm, EntryCreationForm
from .models import News, Entry, Review, AuthorInf
from django.db import connection
from profile_app.views import upload_image
from .custom_decorators import authority_required


def home(request):
    news_list = News.get_top_news()
    rest_news_list = News.get_rest_news()

    paginator = Paginator(rest_news_list, 8)
    page_number = request.GET.get('page')

    try:
        rest_news_page = paginator.page(page_number)
    except PageNotAnInteger:
        rest_news_page = paginator.page(1)
    except EmptyPage:
        rest_news_page = paginator.page(paginator.num_pages)

    rec_users_items = None
    colour_list = {1: "hotpink", 2: "#DED82A", 3: "#32AA4D", 4: "#18DDD4"}
    recs = None
    if request.user.is_authenticated:
        recs = request.user.recommendations

        if recs:
            with connection.cursor() as cursor:
                query = """
                        WITH query AS (
                            SELECT p2.id AS p2_id, ui2.username, ec.id AS ec_id, ec.category_name, 
                            COUNT(e.id)::FLOAT / subquery.count_e::FLOAT AS divided_count
                            FROM user_inf ui
                            JOIN profile p ON p.user_inf = ui.id AND p.id = %(profile_id)s
                            JOIN mark m ON m.profile = p.id AND m.mark_name = 'finished'
                            JOIN list_entry le ON le.mark = m.id
                            JOIN entry e ON e.id = le.entry
                            JOIN entry_type et ON et.id = e.entry_type
                            JOIN entry_category ec ON ec.id = et.entry_category
                            JOIN list_entry le2 ON le2.entry = e.id
                            JOIN mark m2 ON m2.id = le2.mark AND m2.mark_name = 'finished'
                            JOIN profile p2 ON p2.id = m2.profile
                            JOIN user_inf ui2 ON ui2.id = p2.user_inf AND ui2.id != ui.id
                            JOIN (
                                SELECT ec.id AS category_id, COUNT(e.id) AS count_e 
                                FROM user_inf ui
                                JOIN profile p ON p.user_inf = ui.id AND p.id = %(profile_id)s
                                JOIN mark m ON m.profile = p.id AND m.mark_name = 'finished'
                                JOIN list_entry le ON le.mark = m.id
                                JOIN entry e ON e.id = le.entry
                                JOIN entry_type et ON et.id = e.entry_type
                                JOIN entry_category ec ON ec.id = et.entry_category
                                GROUP BY ec.id
                            ) AS subquery ON ec.id = subquery.category_id
                            LEFT JOIN friend f ON (f.user1 = ui.id AND f.user2 = ui2.id)
                            OR (f.user1 = ui2.id AND f.user2 = ui.id)
                            WHERE f.user1 IS NULL
                            GROUP BY ui2.id, p2_id, ec.id, subquery.count_e
                        ),
                        summed_counts AS (
                            SELECT p2_id, username, SUM(divided_count) AS sum_divided_count
                            FROM query
                            GROUP BY p2_id, username
                            ORDER BY sum_divided_count DESC
                            LIMIT 5
                        )
                        SELECT query.p2_id, query.username, query.ec_id, query.category_name, query.divided_count,
                        SUM(query.divided_count) OVER (PARTITION BY query.username) AS sum_divided_count
                        FROM query
                        WHERE query.username IN (SELECT username FROM summed_counts)
                        ORDER BY sum_divided_count DESC, query.username;
                    """
                cursor.execute(query, {"profile_id": request.user.profile_set.get().id})
                recommendations = cursor.fetchall()
                # print(recommendations)

                rec_users = {}
                for recommendation in recommendations:
                    if (recommendation[0], recommendation[1]) in rec_users.keys():
                        rec_users[(recommendation[0], recommendation[1])].append((recommendation[2], recommendation[3],
                                    round(recommendation[4]*100, 1), colour_list[recommendation[2]]))
                    else:
                        rec_users[(recommendation[0], recommendation[1])] = [(recommendation[2], recommendation[3],
                                    round(recommendation[4]*100, 1), colour_list[recommendation[2]])]
                # print(rec_users)
                if rec_users:
                    rec_users_items = rec_users.items()

    content = {
        "title": "Home",
        "news_list": news_list,
        "rest_news_page": rest_news_page,
        "rec_users_items": rec_users_items,
        "authenticated": request.user.is_authenticated,
        "recs": recs,
    }
    return render(request, 'catalogue/home.html', content)


def hide_recs(request):
    if request.method == 'POST':
        if request.user.recommendations:
            request.user.recommendations = False
        else:
            request.user.recommendations = True
        request.user.save()
    return redirect('app_home')


def display_news(request, news_id):
    news = News.objects.filter(id=news_id).first()
    content = {
        "title": "News",
        "news": news,
    }
    return render(request, 'catalogue/newscontent.html', content)


@login_required
@authority_required
def add_news(request):
    image_is_valid = True
    if request.method == 'POST':
        form = NewsCreationForm(user=request.user, data=request.POST)
        if form.is_valid():
            title = form.cleaned_data['title']
            message = form.cleaned_data['message']
            with connection.cursor() as cursor:
                query = """
                        INSERT INTO news(title, message, author) VALUES(%(title)s,
                        %(message)s, %(user_id)s) RETURNING id
                    """
                cursor.execute(query, {"title": title, "message": message, "user_id": request.user.id})
                news_id = cursor.fetchone()[0]
                connection.commit()

            image_is_valid, image_name = upload_image(request, 'upload_image', 'news')
            if image_name:
                News.objects.filter(id=news_id).update(image=basename(image_name))
            if image_is_valid:
                return redirect('app_home')
    else:
        form = NewsCreationForm(user=request.user)

    content = {
        "title": "Add News",
        "form": form,
        "image_is_valid": image_is_valid,
    }
    return render(request, 'catalogue/editnews.html', content)


@login_required
@authority_required
def edit_news(request, news_id):
    image_is_valid = True
    news_instance = News.objects.filter(id=news_id).first()
    if request.method == 'POST':
        form = NewsCreationForm(instance=news_instance, user=request.user, data=request.POST)
        if form.is_valid():
            title = form.cleaned_data['title']
            message = form.cleaned_data['message']
            with connection.cursor() as cursor:
                query = "UPDATE news SET title = %(title)s, message = %(message)s WHERE id = %(news_id)s"
                cursor.execute(query, {"title": title, "message": message, "news_id": news_id})
                connection.commit()

            image_is_valid, image_name = upload_image(request, 'upload_image', 'news')
            if image_name:
                News.objects.filter(id=news_id).update(image=basename(image_name))
            if image_is_valid:
                return redirect('app_news', news_id)
    else:
        form = NewsCreationForm(instance=news_instance, user=request.user)

    content = {
        "title": "Edit News",
        "form": form,
        "image_is_valid": image_is_valid,
    }
    return render(request, 'catalogue/editnews.html', content)


def catalogue(request):
    search_string = request.GET.get('entry-search', '').strip()
    category_id = request.GET.get('dropdown')

    perform_search = True

    with connection.cursor() as cursor:
        query = "SELECT id, category_name from entry_category;"
        cursor.execute(query)
        entry_categories = cursor.fetchall()

    if search_string:
        if category_id == 'all':
            category_names = search_all(search_string)
        elif category_id == 'user':
            category_names = search_user(search_string)
        elif category_id == 'author':
            category_names = search_author(search_string)
        else:
            category_names = search_entry(category_id, search_string)
    elif any(category_id == str(cat[0]) for cat in entry_categories):
        category_names = search_category(category_id)
    else:
        category_names = display_catalogue()
        perform_search = False

    grouped_entries = defaultdict(list)
    for title, cover_img, category_name, entry_id in category_names:
        grouped_entries[category_name].append((title, cover_img, entry_id))

    content = {
        "title": "Catalogue",
        "grouped_entries": grouped_entries.items(),
        "entry_categories": entry_categories,
        "perform_search": perform_search,
        "search_string": search_string,
    }
    return render(request, 'catalogue/catalogue.html', content)


def display_entry(request, entry_id):
    if not Entry.objects.filter(id=entry_id).first() or not Entry.objects.filter(id=entry_id).first().confirmed:
        return redirect('app_catalogue')
    entry_link = Entry.objects.filter(id=entry_id).first()
    marks = None
    non_default_marks = None
    rate = None
    entry_links = None
    profile_id = None
    review_var = None
    review_value_reply = None
    review_display_value_reply = None
    if request.user.is_authenticated:
        authority = request.user.user_role.id < 3
    else:
        authority = False
    if request.method == 'POST':
        submit_button = request.POST.get('submit-btn')
        if submit_button == 'button-upload':
            review_reply = request.POST.get('review_reply')
            review_display_reply = request.POST.get('review_display_reply')
            upload_review(request, entry_id, request.POST.get('review_value_upload'),
                                         review_reply, review_display_reply)
            return redirect('app_entry', entry_id)
        elif submit_button == 'button-edit':
            review_id = request.POST.get('review_value_edit')
            review_var = Review.objects.filter(id=review_id).first()
        else:
            review_value_reply = request.POST.get('review_value_reply')
            review_display_value_reply = request.POST.get('review_value_display_reply')
            if not review_value_reply:
                review_value_reply = review_display_value_reply

    with connection.cursor() as cursor:
        query = """
                SELECT title, alt_title, e.add_date, fin_date, plan_date, description,
                country, production, cover_img, et.type_name, ec.category_name, ec.id, cur_parts, total_parts
                FROM entry e
                JOIN entry_type et ON et.id = e.entry_type
                JOIN entry_category ec ON ec.id = et.entry_category
                WHERE e.id = %(entry_id)s AND e.confirmed;
            """
        cursor.execute(query, {"entry_id": entry_id})
        entry = cursor.fetchone()

        query = """
                SELECT AVG(rate) from list_entry le
                JOIN entry e ON e.id = le.entry
                WHERE e.id = %(entry_id)s
                GROUP BY e.id;
            """
        cursor.execute(query, {"entry_id": entry_id})
        total_rating = cursor.fetchone()
        if total_rating:
            total_rating = total_rating[0]
        if total_rating:
            total_rating = round(total_rating, 1)

        query = """
                SELECT tag_name FROM tag t 
                JOIN entry_tag etg ON etg.tag = t.id
                JOIN entry e ON etg.entry = e.id
                WHERE e.id = %(entry_id)s;
            """
        cursor.execute(query, {"entry_id": entry_id})
        entry_tags = cursor.fetchall()
        if entry_tags:
            entry_tags_formatted = ', '.join(tag[0] for tag in entry_tags)
        else:
            entry_tags_formatted = None

        query = """
                SELECT ai.author_name, string_agg(ea.author_role, ', ') AS roles
                FROM author_inf ai
                JOIN entry_author ea ON ea.author = ai.id
                JOIN entry e ON e.id = ea.entry
                WHERE e.id = %(entry_id)s AND e.confirmed
                GROUP BY ai.author_name;
            """
        cursor.execute(query, {"entry_id": entry_id})
        entry_authors = cursor.fetchall()

        if entry_link.franchise:
            franchise_id = entry_link.franchise.id
            query = """
                    SELECT e.id, e.title, ec.id FROM entry e
                    JOIN entry_type et ON et.id = e.entry_type
                    JOIN entry_category ec ON ec.id = et.entry_category
                    WHERE e.id != %(entry_id)s AND e.franchise = %(franchise_id)s AND e.confirmed ORDER BY 
                    CASE WHEN add_date IS NOT NULL THEN add_date ELSE NULL END,
                    CASE WHEN add_date IS NULL AND plan_date IS NOT NULL THEN plan_date ELSE NULL END, e.id;
                """
            cursor.execute(query, {"franchise_id": franchise_id, "entry_id": entry_id})
            entry_links = cursor.fetchall()

        query = """
                SELECT message, review.add_date, ui.username, p.picture, p.id, ui.id, review.id FROM review
                JOIN entry e ON e.id = review.entry
                LEFT JOIN user_inf ui ON ui.id = review.author
                LEFT JOIN profile p ON p.user_inf = ui.id
                WHERE e.id = %(entry_id)s AND review.reply_display IS NULL
                ORDER BY review.add_date DESC;
            """
        cursor.execute(query, {"entry_id": entry_id})
        reviews = cursor.fetchall()

        query = """
                SELECT message, review.add_date, ui.username, p.picture, p.id, ui.id, review.id,
                reply, reply_display FROM review
                JOIN entry e ON e.id = review.entry
                LEFT JOIN user_inf ui ON ui.id = review.author
                LEFT JOIN profile p ON p.user_inf = ui.id
                WHERE e.id = %(entry_id)s AND review.reply_display IS NOT NULL
                ORDER BY review.id ASC;
            """
        cursor.execute(query, {"entry_id": entry_id})
        reviews_reply = cursor.fetchall()

        review_ids = [review[6] for review in reviews]
        review_reply_dict = {}
        for review_id in review_ids:
            related_replies = [review_reply for review_reply in reviews_reply if review_reply[8] == review_id]
            review_reply_dict[review_id] = related_replies

        if request.user.is_authenticated:
            profile_id = request.user.profile_set.get().id

            query = """
                    SELECT mark_name, mark.id,
                        CASE WHEN mark.id = (
                            SELECT mark.id FROM mark
                            JOIN list_entry le ON mark.id = le.mark
                            JOIN entry e ON e.id = le.entry
                            WHERE mark.profile = %(profile_id)s AND e.id = %(entry_id)s AND is_default
                        ) THEN true ELSE false END AS selected
                    FROM mark
                    WHERE mark.profile = %(profile_id)s AND is_default;
                """
            cursor.execute(query, {"profile_id": profile_id, "entry_id": entry_id})
            marks = cursor.fetchall()

            query = """
                    SELECT mark_name, mark.id,
                        CASE WHEN mark.id in (
                            SELECT mark.id FROM mark
                            JOIN list_entry le ON mark.id = le.mark
                            JOIN entry e ON e.id = le.entry
                            WHERE mark.profile = %(profile_id)s AND e.id = %(entry_id)s AND is_default = FALSE
                        ) THEN true ELSE false END AS selected
                    FROM mark
                    WHERE mark.profile = %(profile_id)s AND is_default = FALSE;
                """
            cursor.execute(query, {"profile_id": profile_id, "entry_id": entry_id})
            non_default_marks = cursor.fetchall()

            query = """
                    SELECT rate FROM list_entry le
                    JOIN mark m ON m.id = le.mark
                    WHERE entry = %(entry_id)s AND m.profile = %(profile_id)s AND rate IS NOT NULL;
                """
            cursor.execute(query, {"profile_id": profile_id, "entry_id": entry_id})
            rate_dec = cursor.fetchone()
            if rate_dec:
                rate = rate_dec[0]

    paginator = Paginator(reviews, 10)
    page_number = request.GET.get('page')

    try:
        reviews_page = paginator.page(page_number)
    except PageNotAnInteger:
        reviews_page = paginator.page(1)
    except EmptyPage:
        reviews_page = paginator.page(paginator.num_pages)

    content = {
        "title": "Catalogue Entry",
        "entry": entry,
        "entry_tags": entry_tags_formatted,
        "entry_authors": entry_authors,
        "entry_links": entry_links,
        "marks": marks,
        "non_default_marks": non_default_marks,
        "logged_in": request.user.is_authenticated,
        "rating": range(1, 11),
        "entry_id": entry_id,
        "rate": rate,
        "total_rating": total_rating,
        "profile_id": profile_id,
        "reviews": reviews,
        "reviews_page": reviews_page,
        "reviews_replies": review_reply_dict.items(),
        "review_var": review_var,
        "review_reply": review_value_reply,
        "review_display_reply": review_display_value_reply,
        "authority": authority,
    }
    return render(request, 'catalogue/entry.html', content)


@login_required
def upload_review(request, entry_id, review_id=None, review_reply=None, review_display_reply=None):
    review_message = request.POST.get('review_message')
    if review_message:
        with connection.cursor() as cursor:
            if review_id:
                query = """
                        UPDATE review SET message = NULLIF(%(review_message)s, '')
                        WHERE id = %(review_id)s and author = %(user_id)s;
                    """
                cursor.execute(query, {"review_message": review_message,
                                       "review_id": review_id, "user_id": request.user.id})
            else:
                if not review_reply:
                    review_reply = None
                if not review_display_reply:
                    review_display_reply = None
                query = """
                        INSERT INTO review(message, entry, author, reply, reply_display)
                        VALUES (NULLIF(%(review_message)s, ''), %(entry_id)s, %(author_id)s,
                        %(review_reply)s, %(review_display_reply)s);
                    """
                cursor.execute(query, {"review_message": review_message,
                                       "entry_id": entry_id, "author_id": request.user.id,
                                       "review_reply": review_reply, "review_display_reply": review_display_reply})
            connection.commit()


@login_required
def delete_review(request, entry_id):
    if request.method == 'POST':
        review_id = request.POST.get('review_value')
        review = Review.objects.filter(id=review_id).first()
        if review.author == request.user:
            with connection.cursor() as cursor:
                query = "DELETE FROM review WHERE reply_display = %(review_id)s"
                cursor.execute(query, {"review_id": review_id})
                query = "DELETE FROM review WHERE id = %(review_id)s"
                cursor.execute(query, {"review_id": review_id})
                connection.commit()
    return redirect('app_entry', entry_id)


@login_required
def add_entry(request):
    image_is_valid = True
    date_selection = None
    add_date = None
    fin_date = None
    plan_date = None
    entry_category = None
    entry_type_val = None
    franchise_name = None
    new_franchise_name = None
    tags_selected = []
    error_for_date = None
    existing_title = None
    user_role = request.user.user_role.id
    if request.method == 'POST':
        add_date = request.POST.get('add_date')
        fin_date = request.POST.get('fin_date')
        plan_date = request.POST.get('plan_date')
        if plan_date:
            plan_date = int(plan_date)
        e_form = EntryCreationForm(request.POST)
        entry_category = request.POST.get('category-selection')
        entry_category = int(entry_category) if entry_category else None
        franchise_id = request.POST.get('franchise-hidden') or None
        franchise_name = request.POST.get('franchise-input')
        new_franchise_name = request.POST.get('new-franchise')
        entry_type_val = request.POST.get('entry_type')
        if entry_type_val:
            entry_type_val = int(entry_type_val)
        tag_list = request.POST.getlist('tag-list')
        tags_selected = [int(tag_l) for tag_l in tag_list if tag_list]
        authors_selected = []
        for i in range(1, 11):
            new_roles = []
            author_hidden = request.POST.get(f'author-hidden-{i}')
            new_author = request.POST.get(f'new-author-{i}')
            for j in range(1, 4):
                new_role = request.POST.get(f'author-role-{i}-{j}')
                if new_role:
                    new_roles.append(new_role)
            if author_hidden:
                author_hidden = int(author_hidden)
            if (new_author or author_hidden) and new_roles:
                authors_selected.append((author_hidden, new_author, new_roles))
        image_is_valid, image_name = upload_image(request, 'upload_image', 'catalogue')
        if 'confirmed' not in request.session:
            with connection.cursor() as cursor:
                query = "SELECT title FROM entry WHERE title = %(title)s LIMIT 1"
                cursor.execute(query, {"title": request.POST.get('title')})
                existing_title = cursor.fetchone()
                if existing_title:
                    existing_title = existing_title[0]
            request.session['confirmed'] = True
        if e_form.is_valid() and authors_selected and tag_list and image_is_valid:
            request.session.pop('confirmed', None)
            title = e_form.cleaned_data['title'] or None
            alt_title = e_form.cleaned_data['alt_title'] or None
            add_date = e_form.cleaned_data['add_date'] or None
            fin_date = e_form.cleaned_data['fin_date'] or None
            description = e_form.cleaned_data['description'] or None
            country = e_form.cleaned_data['country'] or None
            production = e_form.cleaned_data['production'] or None
            entry_type = e_form.cleaned_data['entry_type'] or None
            plan_date = e_form.cleaned_data['plan_date'] or None
            cur_parts = e_form.cleaned_data['cur_parts'] or None
            total_parts = e_form.cleaned_data['total_parts'] or None
            if add_date:
                plan_date = None
            confirmed = user_role < 3
            with connection.cursor() as cursor:
                if not franchise_id and new_franchise_name:
                    query = """
                            INSERT INTO franchise(franchise_name, confirmed) 
                            VALUES(%(new_franchise_name)s, %(confirmed)s) RETURNING id
                        """
                    cursor.execute(query, {"new_franchise_name": new_franchise_name, "confirmed": confirmed})
                    franchise_id = cursor.fetchone()[0]

                query = """
                        INSERT INTO entry(title, alt_title, add_date, fin_date, description, country, production,
                        entry_type, plan_date, franchise, cur_parts, total_parts, confirmed)
                        VALUES(%(title)s, %(alt_title)s, %(add_date)s, %(fin_date)s, %(description)s, %(country)s,
                        %(production)s, %(entry_type)s, %(plan_date)s, %(franchise)s, %(cur_parts)s, %(total_parts)s,
                        %(confirmed)s) RETURNING id;
                    """
                cursor.execute(query, {"title": title, "alt_title": alt_title, "add_date": add_date,
                                       "fin_date": fin_date, "description": description, "country": country,
                                       "production": production, "entry_type": entry_type.id, "plan_date": plan_date,
                                       "franchise": franchise_id, "cur_parts": cur_parts, "total_parts": total_parts,
                                       "confirmed": confirmed})
                new_entry_id = cursor.fetchone()[0]

                for author_selected in authors_selected:
                    if author_selected[1]:
                        query = """
                                INSERT INTO author_inf(author_name, confirmed) 
                                VALUES(%(author_name)s, %(confirmed)s) RETURNING id
                            """
                        cursor.execute(query, {"author_name": author_selected[1], "confirmed": confirmed})
                        author_id = cursor.fetchone()[0]
                    else:
                        author_id = author_selected[0]
                    for r in author_selected[2]:
                        query = """
                                INSERT INTO entry_author(author, entry, author_role)
                                VALUES(%(author)s, %(entry)s, %(author_role)s)
                            """
                        cursor.execute(query, {"author": author_id, "entry": new_entry_id,
                                               "author_role": r})

                for tag_l in tag_list:
                    query = "INSERT INTO entry_tag(tag, entry) VALUES(%(tag)s, %(entry)s)"
                    cursor.execute(query, {"tag": tag_l, "entry": new_entry_id})

                if not confirmed:
                    query = """
                            SELECT ui.id FROM user_inf ui
                            LEFT JOIN entry_user eu ON ui.id = eu.user_inf
                            LEFT JOIN (
                                SELECT user_inf, MAX(add_date) AS latest_add_date
                                FROM entry_user
                                GROUP BY user_inf
                            ) AS latest_dates ON eu.user_inf = latest_dates.user_inf
                            WHERE user_role = 2
                            GROUP BY ui.id, latest_dates.latest_add_date
                            ORDER BY latest_dates.latest_add_date NULLS FIRST, COUNT(eu.user_inf)
                            LIMIT 1;
                        """
                    cursor.execute(query)
                    moderator_id = cursor.fetchone()

                    query = "INSERT INTO entry_user(entry, user_inf) VALUES(%(entry)s, %(user_inf)s)"
                    cursor.execute(query, {"entry": new_entry_id, "user_inf": moderator_id})

                connection.commit()
            if image_name:
                Entry.objects.filter(id=new_entry_id).update(cover_img=basename(image_name))
            if image_is_valid:
                return redirect('app_catalogue')
    else:
        request.session.pop('confirmed', None)
        e_form = EntryCreationForm()

    current_year = datetime.now().year
    with connection.cursor() as cursor:
        query = "SELECT id, category_name FROM entry_category;"
        cursor.execute(query)
        categories = cursor.fetchall()

        query = """
                SELECT et.id, et.type_name, ec.id, ec.category_name FROM entry_type et
                JOIN entry_category ec ON ec.id = et.entry_category;
            """
        cursor.execute(query)
        types = cursor.fetchall()

        query = "SELECT id, tag_name FROM tag;"
        cursor.execute(query)
        tags = cursor.fetchall()

        query = "SELECT id, author_name FROM author_inf WHERE confirmed;"
        cursor.execute(query)
        authors = cursor.fetchall()

        query = "SELECT id, franchise_name FROM franchise WHERE confirmed;"
        cursor.execute(query)
        franchises = cursor.fetchall()
    content = {
        "title": "Add entry",
        "add_entry_form": True,
        "e_form": e_form,
        "range": range(current_year, current_year+11),
        "categories": categories,
        "types": types,
        "tags": tags,
        "authors": authors,
        "franchises": franchises,
        "date_selection": date_selection,
        "add_date": add_date,
        "fin_date": fin_date,
        "plan_date": plan_date,
        "entry_category": entry_category,
        "entry_type_val": entry_type_val,
        "franchise_name": franchise_name,
        "new_franchise_name": new_franchise_name,
        "tags_selected": tags_selected,
        "error_date_selection": error_for_date,
        "image_is_valid": image_is_valid,
        "existing_title": existing_title,
    }
    return render(request, 'catalogue/editentry.html', content)


@login_required
@authority_required
def edit_entry(request, entry_id):
    image_is_valid = True
    franchise_name = None
    new_franchise_name = None
    error_for_date = None
    authors_selected = None
    roles_from_authors = None
    entry_franchise_id = None
    entry = Entry.objects.filter(id=entry_id).first()
    if entry and entry.franchise:
        entry_franchise_id = entry.franchise.id
    if request.method == 'POST':
        submit_button = request.POST.get('btn-submit')
        if submit_button == 'btn-delete':
            with connection.cursor() as cursor:
                query = "DELETE FROM entry WHERE id = %(entry_id)s"
                cursor.execute(query, {"entry_id": int(entry_id)})
                connection.commit()
            return redirect('app_catalogue')
        date_selection = request.POST.get('date_selection')
        add_date = request.POST.get('add_date')
        if add_date:
            add_date = parse_date(add_date)
        fin_date = request.POST.get('fin_date')
        if fin_date:
            fin_date = parse_date(fin_date)
        plan_date = request.POST.get('plan_date')
        if plan_date:
            plan_date = int(plan_date)
        e_form = EntryCreationForm(instance=entry, data=request.POST,
                                   initial={'date_selection': date_selection, 'add_date': add_date,
                                            'fin_date': fin_date, 'plan_date': plan_date})
        entry_category = request.POST.get('category-selection')
        entry_category = int(entry_category) if entry_category else None
        franchise_id = request.POST.get('franchise-hidden') or None
        franchise_name = request.POST.get('franchise-input')
        new_franchise_name = request.POST.get('new-franchise')
        entry_type_val = request.POST.get('entry_type')
        if entry_type_val:
            entry_type_val = int(entry_type_val)
        tag_list = request.POST.getlist('tag-list')
        tags_selected = [int(tag_l) for tag_l in tag_list if tag_list]
        authors_selected = []
        for i in range(1, 11):
            new_roles = []
            author_hidden = request.POST.get(f'author-hidden-{i}')
            author_name = ''
            new_author = request.POST.get(f'new-author-{i}')
            author_valid = False
            for j in range(1, 4):
                new_role = request.POST.get(f'author-role-{i}-{j}')
                if new_role:
                    new_roles.append(new_role)
                    author_valid = True
                else:
                    new_roles.append('')
            if author_hidden:
                author_hidden = int(author_hidden)
                author_name = AuthorInf.objects.filter(id=author_hidden).first().author_name
            if (new_author or author_hidden) and author_valid:
                authors_selected.append((author_hidden, new_author, new_roles, author_name))
        for i in range(len(authors_selected)+1, 11):
            authors_selected.append(('', '', ['', '', '']))
        image_is_valid, image_name = upload_image(request, 'upload_image', 'catalogue')
        if e_form.is_valid() and authors_selected and tag_list and image_is_valid:
            title = e_form.cleaned_data['title'] or None
            alt_title = e_form.cleaned_data['alt_title'] or None
            add_date = e_form.cleaned_data['add_date'] or None
            fin_date = e_form.cleaned_data['fin_date'] or None
            description = e_form.cleaned_data['description'] or None
            country = e_form.cleaned_data['country'] or None
            production = e_form.cleaned_data['production'] or None
            entry_type = e_form.cleaned_data['entry_type'] or None
            plan_date = e_form.cleaned_data['plan_date'] or None
            cur_parts = e_form.cleaned_data['cur_parts']
            total_parts = e_form.cleaned_data['total_parts']
            if add_date:
                plan_date = None
            with connection.cursor() as cursor:
                if entry.franchise:
                    new_franchise_id = entry.franchise.id
                else:
                    new_franchise_id = franchise_id
                if entry.franchise and new_franchise_name and entry.franchise.franchise_name == new_franchise_name:
                    query = "UPDATE franchise SET confirmed = TRUE WHERE id = %(franchise_id)s"
                    cursor.execute(query, {"franchise_id": entry.franchise.id})
                elif new_franchise_name:
                    query = """
                            INSERT INTO franchise(franchise_name, confirmed)
                            VALUES(%(new_franchise_name)s, TRUE) RETURNING id
                        """
                    cursor.execute(query, {"new_franchise_name": new_franchise_name})
                    new_franchise_id = cursor.fetchone()[0]

                query = """
                    UPDATE entry SET title = %(title)s, alt_title = %(alt_title)s, add_date = %(add_date)s,
                    fin_date = %(fin_date)s, description = %(description)s, country = %(country)s,
                    production = %(production)s, entry_type = %(entry_type)s, plan_date = %(plan_date)s, 
                    franchise = %(franchise)s, cur_parts = %(cur_parts)s, total_parts = %(total_parts)s,
                    confirmed = TRUE WHERE id = %(entry_id)s;
                    """
                cursor.execute(query, {"title": title, "alt_title": alt_title, "add_date": add_date,
                                       "fin_date": fin_date, "description": description, "country": country,
                                       "production": production, "entry_type": entry_type.id, "plan_date": plan_date,
                                       "franchise": new_franchise_id, "cur_parts": cur_parts,
                                       "total_parts": total_parts, "entry_id": entry_id})

                query = "SELECT DISTINCT author FROM entry_author WHERE entry = %(entry)s"
                cursor.execute(query, {"entry": entry_id})
                authors_db = cursor.fetchall()
                authors_db_list = [author_db[0] for author_db in authors_db]
                filtered_authors = [author for author in authors_selected if author[0] or author[1]]

                for author_selected in filtered_authors:
                    if author_selected[0] and author_selected[0] in authors_db_list:
                        query = "UPDATE author_inf SET confirmed = TRUE WHERE id = %(author_id)s"
                        cursor.execute(query, {"author_id": author_selected[0]})
                        query = """
                                SELECT author_role FROM entry_author 
                                WHERE entry=%(entry_id)s AND author=%(author_id)s
                            """
                        cursor.execute(query, {"author_id": author_selected[0], "entry_id": entry_id})
                        roles_db = cursor.fetchall()
                        roles_db_list = [role[0] for role in roles_db]
                        for r in author_selected[2]:
                            if r and r not in roles_db_list:
                                query = """
                                        INSERT INTO entry_author(author, entry, author_role)
                                        VALUES(%(author)s, %(entry)s, %(author_role)s)
                                    """
                                cursor.execute(query, {"author": author_id, "entry": entry_id,
                                                       "author_role": r})
                            elif r:
                                roles_db_list.remove(r)
                        for r in roles_db_list:
                            query = """
                                    DELETE FROM entry_author 
                                    WHERE role=%(r)s AND entry = %(entry)s AND author=%(author)s
                                """
                            cursor.execute(query, {"r": r, "entry": entry_id, "author": author_selected[0]})

                        authors_db_list.remove(author_selected[0])
                    else:
                        if author_selected[0]:
                            author_id = author_selected[0]
                        elif author_selected[1]:
                            query = """
                                    INSERT INTO author_inf(author_name, confirmed) 
                                    VALUES(%(author_name)s, TRUE) RETURNING id
                                """
                            cursor.execute(query, {"author_name": author_selected[1]})
                            author_id = cursor.fetchone()[0]
                        for r in author_selected[2]:
                            if r:
                                query = """
                                        INSERT INTO entry_author(author, entry, author_role)
                                        VALUES(%(author)s, %(entry)s, %(author_role)s)
                                    """
                                cursor.execute(query, {"author": author_id, "entry": entry_id,
                                                       "author_role": r})
                for author_db in authors_db_list:
                    query = "DELETE FROM entry_author WHERE author = %(author)s AND entry=%(entry)s"
                    cursor.execute(query, {"author": author_db, "entry": entry_id})
                    query = "DELETE FROM author_inf WHERE id = %(id)s AND NOT confirmed"
                    cursor.execute(query, {"id": author_db})

                query = "SELECT tag FROM entry_tag WHERE entry = %(entry)s"
                cursor.execute(query, {"entry": entry_id})
                tags_db = cursor.fetchall()
                tags_db_list = [tag_db[0] for tag_db in tags_db]
                for tag_l in tags_selected:
                    if tag_l not in tags_db_list:
                        query = "INSERT INTO entry_tag(tag, entry) VALUES(%(tag)s, %(entry)s)"
                        cursor.execute(query, {"tag": tag_l, "entry": entry_id})
                    else:
                        tags_db_list.remove(tag_l)
                for tag_db in tags_db_list:
                    query = "DELETE FROM entry_tag WHERE tag = %(tag)s AND entry = %(entry)s"
                    cursor.execute(query, {"tag": tag_db, "entry": entry_id})

                connection.commit()
            if image_name:
                Entry.objects.filter(id=entry_id).update(cover_img=basename(image_name))
            if image_is_valid:
                return redirect('app_catalogue')
    else:
        if entry.add_date:
            date_selection = 'confirmed'
        elif entry.plan_date:
            date_selection = 'planned'
        else:
            date_selection = 'nothing'
        e_form = EntryCreationForm(instance=entry, initial={'date_selection': date_selection})
        entry_category = entry.entry_type.entry_category.id
        entry_type_val = entry.entry_type.id
        if entry.franchise:
            if entry.franchise.confirmed:
                franchise_name = entry.franchise.franchise_name
            else:
                franchise_name = 'Not in list'
                new_franchise_name = entry.franchise.franchise_name
        with connection.cursor() as cursor:
            query = "SELECT add_date, fin_date, plan_date FROM entry WHERE id = %(entry_id)s"
            cursor.execute(query, {"entry_id": int(entry_id)})
            dates = cursor.fetchone()
            add_date = dates[0]
            fin_date = dates[1]
            plan_date = dates[2]

            query = """
                    SELECT id FROM tag
                    JOIN entry_tag et ON et.tag = tag.id
                    WHERE entry = %(entry_id)s;
                """
            cursor.execute(query, {"entry_id": int(entry_id)})
            tags_selected_query = cursor.fetchall()
            tags_selected = [t[0] for t in tags_selected_query]

            query = """
                    SELECT DISTINCT ai.id, ai.author_name FROM author_inf ai
                    JOIN entry_author ea ON ea.author = ai.id
                    WHERE ea.entry = %(entry_id)s
                    ORDER BY ai.id;
                """
            cursor.execute(query, {"entry_id": int(entry_id)})
            authors_from_entry = cursor.fetchall()
            roles_from_authors = []
            n = 0
            for au in authors_from_entry:
                query = """
                        SELECT author_role FROM entry_author
                        WHERE author = %(author)s AND entry = %(entry_id)s;
                    """
                cursor.execute(query, {"author": au[0], "entry_id": entry_id})
                roles_from_author = cursor.fetchall()
                roles_from_authors.append((au[0], '', [role[0] for role in roles_from_author]
                                           + [""] * (3 - len(roles_from_author)), au[1]))
                n += 1
            for i in range(n, 11):
                roles_from_authors.append(('', '', ['', '', '']))
    current_year = datetime.now().year
    with connection.cursor() as cursor:
        query = "SELECT id, category_name FROM entry_category;"
        cursor.execute(query)
        categories = cursor.fetchall()

        query = """
                SELECT et.id, et.type_name, ec.id, ec.category_name FROM entry_type et
                JOIN entry_category ec ON ec.id = et.entry_category;
            """
        cursor.execute(query)
        types = cursor.fetchall()

        query = "SELECT id, tag_name FROM tag;"
        cursor.execute(query)
        tags = cursor.fetchall()

        query = """
                SELECT ai.id, ai.author_name FROM author_inf ai WHERE confirmed
                UNION
                SELECT ai.id, ai.author_name FROM author_inf ai
                JOIN entry_author ea ON ea.author = ai.id
                WHERE ea.entry = %(entry_id)s;
            """
        cursor.execute(query, {"entry_id": entry_id})
        authors = cursor.fetchall()

        query = "SELECT id, franchise_name FROM franchise WHERE confirmed;"
        cursor.execute(query)
        franchises = cursor.fetchall()

    content = {
        "title": "Edit entry",
        "edit_entry": True,
        "cover_img": entry.cover_img,
        "e_form": e_form,
        "range": range(current_year, current_year+11),
        "categories": categories,
        "types": types,
        "tags": tags,
        "authors": authors,
        "franchises": franchises,
        "date_selection": date_selection,
        "add_date": add_date,
        "fin_date": fin_date,
        "plan_date": plan_date,
        "entry_category": entry_category,
        "entry_type_val": entry_type_val,
        "franchise_id": entry_franchise_id,
        "franchise_name": franchise_name,
        "new_franchise_name": new_franchise_name,
        "tags_selected": tags_selected,
        "error_date_selection": error_for_date,
        "image_is_valid": image_is_valid,
        "author_count": range(1, 11),
        "author_role_count": range(1, 4),
        "authors_selected": authors_selected or roles_from_authors,
    }
    return render(request, 'catalogue/editentry.html', content)


def update_mark(request, entry_id):
    mark_value = request.GET.get('dropdown-mark', '')

    with connection.cursor() as cursor:
        query = """
                SELECT le.mark FROM list_entry le
                JOIN mark m ON m.id = le.mark
                WHERE entry = %(entry_id)s AND m.profile = %(profile_id)s AND is_default;
            """
        cursor.execute(query, {"entry_id": entry_id, "profile_id": request.user.profile_set.get().id})
        mark_id = cursor.fetchone()

        if mark_value and mark_id:
            query = "UPDATE list_entry SET mark = %(mark_value)s WHERE mark = %(mark_id)s AND entry = %(entry_id)s;"
            cursor.execute(query, {"mark_value": mark_value, "mark_id": mark_id, "entry_id": entry_id})
        elif mark_value:
            query = "INSERT INTO list_entry(entry, mark) VALUES(%(entry_id)s, %(mark_value)s);"
            cursor.execute(query, {"mark_value": mark_value, "entry_id": entry_id})
        else:
            query = "DELETE FROM list_entry WHERE mark = %(mark_id)s AND entry = %(entry_id)s;"
            cursor.execute(query, {"mark_id": mark_id, "entry_id": entry_id})
        connection.commit()

    return redirect('app_entry', entry_id)


def update_rate(request, entry_id):
    rate_value = request.GET.get('dropdown-rate', '')

    with connection.cursor() as cursor:
        query = """
                SELECT m.id FROM list_entry le
                JOIN mark m ON m.id = le.mark
                WHERE entry = %(entry_id)s AND m.profile = %(profile_id)s AND is_default;
            """
        cursor.execute(query, {"entry_id": entry_id, "profile_id": request.user.profile_set.get().id})
        mark_id = cursor.fetchone()
        if rate_value and mark_id:
            query = "UPDATE list_entry SET rate = %(rate_value)s WHERE mark = %(mark_id)s AND entry = %(entry_id)s;"
            cursor.execute(query, {"rate_value": rate_value, "mark_id": mark_id, "entry_id": entry_id})
        elif mark_id:
            query = "UPDATE list_entry SET rate = NULL WHERE mark = %(mark_id)s AND entry = %(entry_id)s;"
            cursor.execute(query, {"mark_id": mark_id, "entry_id": entry_id})
        connection.commit()

    return redirect('app_entry', entry_id)


def update_additional_mark(request, entry_id):
    mark_values = request.GET.getlist('catalogue-list', '')
    mark_ids_req = [int(mark_value) for mark_value in mark_values]
    new_values = mark_ids_req

    with connection.cursor() as cursor:
        query = """
                SELECT le.mark FROM list_entry le
                JOIN mark m ON m.id = le.mark
                WHERE entry = %(entry_id)s AND m.profile = %(profile_id)s AND is_default = FALSE;
            """
        cursor.execute(query, {"entry_id": entry_id, "profile_id": request.user.profile_set.get().id})
        non_default_marks = cursor.fetchall()
        if non_default_marks:
            mark_ids_cur = [mark[0] for mark in non_default_marks]

            set_req = set(mark_ids_req)
            set_cur = set(mark_ids_cur)
            old_values = list(set_cur - set_req)
            new_values = list(set_req - set_cur)

            for v in old_values:
                query = "DELETE FROM list_entry WHERE entry=%(entry_id)s AND mark=%(mark_id)s"
                cursor.execute(query, {"mark_id": v, "entry_id": entry_id})

        for v in new_values:
            query = "INSERT INTO list_entry(entry, mark) VALUES(%(entry_id)s, %(mark_id)s);"
            cursor.execute(query, {"mark_id": v, "entry_id": entry_id})

        connection.commit()

    return redirect('app_entry', entry_id)


def search_all(search_string):
    with connection.cursor() as cursor:
        query = """
                SELECT e_name, e_img, category_name, id
                FROM (
                    SELECT title AS e_name, cover_img AS e_img, category_name, e.id AS id, counts.c
                    FROM entry e
                    LEFT JOIN (
                        SELECT entry, COUNT(id) AS c FROM list_entry
                        GROUP BY entry
                    ) AS counts ON e.id = counts.entry
                    JOIN entry_type et ON et.id = e.entry_type
                    JOIN entry_category ec ON ec.id = et.entry_category
                    WHERE (lower(title) LIKE lower(%(search_str)s) OR lower(alt_title) LIKE lower(%(search_str)s))
                    AND e.confirmed
                    UNION
                    SELECT ui.username AS e_name, p.picture AS e_img, 'user' AS category_name, p.id AS id, NULL AS c
                    FROM user_inf ui
                    JOIN profile p ON p.user_inf = ui.id
                    WHERE lower(ui.username) LIKE lower(%(search_str)s)
                    UNION
                    SELECT ai.author_name AS e_name, ai.picture AS e_img,
                    'author' AS category_name, ai.id AS id, NULL AS c FROM author_inf ai
                    WHERE lower(ai.author_name) LIKE lower(%(search_str)s) AND ai.confirmed
                ) AS combined_result
                ORDER BY
                CASE 
                    WHEN category_name = 'user' THEN 2
                    WHEN category_name = 'author' THEN 1
                    ELSE 0
                END,
                category_name ASC,
                c DESC NULLS LAST;
            """

        cursor.execute(query, {"search_str": '%' + search_string + '%'})
        category_names = cursor.fetchall()
    return category_names


def search_category(category_id):
    with connection.cursor() as cursor:
        query = """
                SELECT title, cover_img, category_name, e.id FROM entry e
                LEFT JOIN (
                    SELECT entry, COUNT(id) AS c FROM list_entry
                    GROUP BY entry
                ) AS counts ON e.id = counts.entry
                JOIN entry_type et ON et.id = e.entry_type
                JOIN entry_category ec ON ec.id = et.entry_category
                WHERE ec.id = %(category_id)s AND e.confirmed
                ORDER BY c DESC NULLS LAST;
            """

        cursor.execute(query, {"category_id": category_id})
        category_names = cursor.fetchall()
    return category_names


def search_entry(category_id, search_string):
    with connection.cursor() as cursor:
        query = """
                SELECT title, cover_img, category_name, e.id FROM entry e
                LEFT JOIN (
                    SELECT entry, COUNT(id) AS c FROM list_entry
                    GROUP BY entry
                ) AS counts ON e.id = counts.entry
                JOIN entry_type et ON et.id = e.entry_type
                JOIN entry_category ec ON ec.id = et.entry_category
                WHERE ec.id = %(category_id)s AND e.confirmed AND
                (lower(title) LIKE lower(%(search_str)s) OR lower(alt_title) LIKE lower(%(search_str)s))
                ORDER BY c DESC NULLS LAST;
            """

        cursor.execute(query, {"category_id": category_id, "search_str": '%' + search_string + '%'})
        category_names = cursor.fetchall()
    return category_names


def search_user(search_string):
    with connection.cursor() as cursor:
        query = """
                SELECT ui.username, p.picture, 'user', p.id FROM user_inf ui
                JOIN profile p ON p.user_inf = ui.id
                WHERE lower(ui.username) LIKE lower(%(search_str)s);
            """

        cursor.execute(query, {"search_str": '%' + search_string + '%'})
        category_names = cursor.fetchall()
    return category_names


def search_author(search_string):
    with connection.cursor() as cursor:
        query = """
                SELECT ai.author_name, ai.picture, 'author', ai.id FROM author_inf ai
                WHERE lower(ai.author_name) LIKE lower(%(search_str)s) AND ai.confirmed;
            """

        cursor.execute(query, {"search_str": '%' + search_string + '%'})
        category_names = cursor.fetchall()
    return category_names


def display_catalogue():
    with connection.cursor() as cursor:
        query = """
                SELECT title, cover_img, category_name, e.id from entry e
                JOIN entry_type et ON et.id = e.entry_type
                JOIN entry_category ec ON ec.id = et.entry_category
                WHERE e.confirmed
                ORDER BY e.id DESC;
            """

        cursor.execute(query)
        category_names = cursor.fetchall()
    return category_names


def handle_400(request, *args, **argv):
    return render(request, 'error/400.html')


def handle_403(request, *args, **argv):
    return render(request, 'error/403.html')


def handle_404(request, *args, **argv):
    return render(request, 'error/404.html')


def handle_500(request, *args, **argv):
    return render(request, 'error/500.html')


def handle_503(request, *args, **argv):
    return render(request, 'error/503.html')
