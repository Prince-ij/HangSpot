import os

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_migrate import Migrate
from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from hangspot.models import (
    User,
    base_url,
    db,
    hangout_updates,
    likes,
    user_liked_post,
    users,
    wifi_updates,
)

load_dotenv()

app = Flask(__name__)
migrate = Migrate(app, db)
login_manager = LoginManager()

UPLOAD_FOLDER = f"{os.path.join(base_url, 'static/images')}"

login_manager.init_app(app)

app.secret_key = os.getenv("SECRET_KEY")


@login_manager.user_loader
def load_user(user_id):
    query = users.select().where(users.c.id == user_id)
    user = db.execute(query).fetchone()
    if user:
        return User(user)


def save_and_get_image_location(image):
    image_name = secure_filename(image.filename)
    image_path = os.path.join(UPLOAD_FOLDER, image_name)
    image.save(image_path)
    return f"/static/images/{image_name}"


def fetch_wifi_updates():
    wifi_query = (
        select(
            wifi_updates,
            users.c.username.label("updater"),
            func.count(likes.c.id).label("likes_count"),
        )
        .select_from(
            wifi_updates.outerjoin(
                likes, wifi_updates.c.id == likes.c.wifi_id
            ).outerjoin(users, wifi_updates.c.user_id == users.c.id)
        )
        .group_by(wifi_updates.c.id, users.c.username)
    )

    wifi_results = db.execute(wifi_query).fetchall()
    updates = [{"type": "Wifi", **dict(row._mapping)} for row in wifi_results]
    return updates


def fetch_hangout_updates():
    hangout_query = (
        select(
            hangout_updates,
            users.c.username.label("updater"),
            func.count(likes.c.id).label("likes_count"),
        )
        .select_from(
            hangout_updates.outerjoin(
                likes, hangout_updates.c.id == likes.c.hangout_id
            ).outerjoin(users, hangout_updates.c.user_id == users.c.id)
        )
        .group_by(hangout_updates.c.id, users.c.username)
    )

    hangout_results = db.execute(hangout_query).fetchall()
    updates = [{"type": "Hangout", **dict(row._mapping)} for row in hangout_results]
    return updates


def fetch_user_updates_with_likes():
    wifi_query = (
        select(wifi_updates, func.count(likes.c.id).label("likes_count"))
        .select_from(
            wifi_updates.outerjoin(likes, wifi_updates.c.id == likes.c.wifi_id)
        )
        .where(wifi_updates.c.user_id == current_user.id)
        .group_by(wifi_updates.c.id)
    )
    wifi_results = db.execute(wifi_query).fetchall()

    hangout_query = (
        select(hangout_updates, func.count(likes.c.id).label("likes_count"))
        .select_from(
            hangout_updates.outerjoin(likes, hangout_updates.c.id == likes.c.hangout_id)
        )
        .where(hangout_updates.c.user_id == current_user.id)
        .group_by(hangout_updates.c.id)
    )

    hangout_results = db.execute(hangout_query).fetchall()

    wifi = [{"type": "Wifi", **dict(row._mapping)} for row in wifi_results]
    hangouts = [{"type": "Hangout", **dict(row._mapping)} for row in hangout_results]

    user_updates = wifi + hangouts
    return user_updates


def fetch_all_updates_with_likes():
    wifi_query = (
        select(
            wifi_updates,
            users.c.username.label("updater"),
            func.count(likes.c.id).label("likes_count"),
        )
        .select_from(
            wifi_updates.outerjoin(
                likes, wifi_updates.c.id == likes.c.wifi_id
            ).outerjoin(users, wifi_updates.c.user_id == users.c.id)
        )
        .group_by(wifi_updates.c.id, users.c.username)
    )
    wifi_results = db.execute(wifi_query).fetchall()

    hangout_query = (
        select(
            hangout_updates,
            users.c.username.label("updater"),
            func.count(likes.c.id).label("likes_count"),
        )
        .select_from(
            hangout_updates.outerjoin(
                likes, hangout_updates.c.id == likes.c.hangout_id
            ).outerjoin(users, hangout_updates.c.user_id == users.c.id)
        )
        .group_by(hangout_updates.c.id, users.c.username)
    )

    hangout_results = db.execute(hangout_query).fetchall()

    wifi = [{"type": "Wifi", **dict(row._mapping)} for row in wifi_results]
    hangouts = [{"type": "Hangout", **dict(row._mapping)} for row in hangout_results]

    user_updates = wifi + hangouts
    return user_updates


@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        name = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        check_user = users.select().where(users.c.username == name)
        check_email = users.select().where(users.c.email == email)
        user_exists = db.execute(check_user).fetchone()
        email_exists = db.execute(check_email).fetchone()

        if email_exists:
            flash("Email already exists, please look for another one", "error")
            return redirect(url_for("register"))

        if user_exists:
            flash("Username already exists, please look for another one", "error")
            return redirect(url_for("register"))

        query = users.insert().values(username=name, password=password, email=email)
        db.execute(query)
        db.commit()

        return redirect(url_for("login"))
    return render_template("join.html")


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        remember = True if request.form.get("remember") else False

        query = users.select().where(users.c.email == email)
        user = db.execute(query).fetchone()

        if not user:
            flash("Invalid email", "error")
            return redirect(url_for("login"))

        if not check_password_hash(user.password, password):
            flash("Invalid password", "error")
            return redirect(url_for("login"))

        user = User(user)
        login_user(user, remember=remember)

        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/")
def home():
    per_page = 5
    page = request.args.get("page", 1, type=int)
    all_updates = fetch_all_updates_with_likes()

    total = len(all_updates)
    start = (page - 1) * per_page
    end = start + per_page
    updates = all_updates[start:end]

    return render_template(
        "index.html",
        user=current_user,
        updates=updates,
        page=page,
        total_pages=(total + per_page - 1) // per_page,
    )


@app.route("/<type>")
def update_on_type(type):
    per_page = 5
    page = request.args.get("page", 1, type=int)
    if type == "Wifi":
        all_updates = fetch_wifi_updates()
        total = len(all_updates)
        start = (page - 1) * per_page
        end = start + per_page
        updates = all_updates[start:end]
    else:
        all_updates = fetch_hangout_updates()
        total = len(all_updates)
        start = (page - 1) * per_page
        end = start + per_page
        updates = all_updates[start:end]
    return render_template(
        "index.html",
        user=current_user,
        updates=updates,
        page=page,
        total_pages=(total + per_page - 1) // per_page,
    )


@app.route("/update/<type>", methods=["POST", "GET"])
def update(type):
    if not current_user.is_active:
        return redirect(url_for("register"))
    if request.method == "POST":
        name = request.form.get("name")
        address = request.form.get("address")
        opening_time = request.form.get("opening time")
        closing_time = request.form.get("closing time")
        description = request.form.get("description")
        image_url = save_and_get_image_location(request.files.get("image"))
        days = [
            "MON" if request.form.get("MON") else None,
            "TUE" if request.form.get("TUE") else None,
            "WED" if request.form.get("WED") else None,
            "THU" if request.form.get("THU") else None,
            "FRI" if request.form.get("FRI") else None,
            "SAT" if request.form.get("SAT") else None,
            "SUN" if request.form.get("SUN") else None,
        ]
        available_days = [day for day in days if day is not None]

        hour_o, min_o = opening_time.split(":")
        hour_c, min_c = closing_time.split(":")

        opening_time = (
            f"{int(hour_o) % 12}:{min_o}PM"
            if int(hour_o) > 12
            else f"{hour_o}:{min_o}AM"
        )
        closing_time = (
            f"{int(hour_c) % 12}:{min_o}PM"
            if int(hour_c) > 12
            else f"{hour_c}:{min_c}AM"
        )

        if type == "wifi":
            wifi = request.form.get("wifi strength")
            query = wifi_updates.insert().values(
                name=name,
                address=address,
                opening_time=opening_time,
                closing_time=closing_time,
                wifi_strength=wifi,
                available_days=str(available_days),
                description=description,
                image=image_url,
                user_id=current_user.id,
            )
            db.execute(query)
            db.commit()
            return redirect(url_for("home"))
        else:
            query = hangout_updates.insert().values(
                name=name,
                address=address,
                opening_time=opening_time,
                closing_time=closing_time,
                available_days=str(available_days),
                description=description,
                image=image_url,
                user_id=current_user.id,
            )
            db.execute(query)
            db.commit()
            return redirect(url_for("home"))
    if type == "wifi":
        return render_template("wifi_update.html")
    else:
        return render_template("hangout_update.html")


@app.route("/update")
def choose_update():
    return render_template("update.html")


@app.route("/profile")
@login_required
def profile():
    user_updates = fetch_user_updates_with_likes()
    print(user_updates)
    return render_template("profile.html", user=current_user, updates=user_updates)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/edit/<update_id>/<type>", methods=["GET", "POST"])
def edit(update_id, type):
    if request.method == "POST":
        name = request.form.get("name")
        address = request.form.get("address")
        opening_time = request.form.get("opening time")
        closing_time = request.form.get("closing time")
        description = request.form.get("description")
        image_url = save_and_get_image_location(request.files.get("image"))
        days = [
            "MON" if request.form.get("MON") else None,
            "TUE" if request.form.get("TUE") else None,
            "WED" if request.form.get("WED") else None,
            "THU" if request.form.get("THU") else None,
            "FRI" if request.form.get("FRI") else None,
            "SAT" if request.form.get("SAT") else None,
            "SUN" if request.form.get("SUN") else None,
        ]
        available_days = [day for day in days if day is not None]

        hour_o, min_o = opening_time.split(":")
        hour_c, min_c = closing_time.split(":")

        opening_time = (
            f"{int(hour_o) % 12}:{min_o}PM"
            if int(hour_o) > 12
            else f"{hour_o}:{min_o}AM"
        )
        closing_time = (
            f"{int(hour_c) % 12}:{min_o}PM"
            if int(hour_c) > 12
            else f"{hour_c}:{min_c}AM"
        )

        if type == "Wifi":
            wifi = request.form.get("wifi strength")
            updating = wifi_updates.update().values(
                name=name,
                address=address,
                opening_time=opening_time,
                closing_time=closing_time,
                wifi_strength=wifi,
                available_days=str(available_days),
                description=description,
                image=image_url,
                user_id=current_user.id,
            ).where(wifi_updates.c.id == update_id)
            db.execute(updating)
            db.commit()
            return redirect(url_for("home"))
        else:
            updating = hangout_updates.update().values(
                name=name,
                address=address,
                opening_time=opening_time,
                closing_time=closing_time,
                available_days=str(available_days),
                description=description,
                image=image_url,
                user_id=current_user.id,
            ).where(hangout_updates.c.id == update_id)
            db.execute(updating)
            db.commit()
            return redirect(url_for("home"))
    if type == "Wifi":
        query = wifi_updates.select().where(wifi_updates.c.id == update_id)
        update = db.execute(query).fetchone()
        return render_template("wifi_update.html", update=update, is_edit=True)
    else:
        query = hangout_updates.select().where(hangout_updates.c.id == update_id)
        update = db.execute(query).fetchone()
        return render_template("hangout_update.html", update=update, is_edit=True)


@app.route("/delete/<update_id>/<type>")
def delete(update_id, type):
    if type == "Wifi":
        query = wifi_updates.delete().where(wifi_updates.c.id == update_id)
        delete_user_like = user_liked_post.delete().where(
            (user_liked_post.c.wifi_update_id == update_id)
            & (user_liked_post.c.user_id == current_user.id)
        )
        db.execute(query)
        db.execute(delete_user_like)
        db.commit()
        return redirect(url_for("profile"))
    else:
        query = hangout_updates.delete().where(hangout_updates.c.id == update_id)
        delete_user_like = user_liked_post.delete().where(
            (user_liked_post.c.hangout_update_id == update_id)
            & (user_liked_post.c.user_id == current_user.id)
        )
        db.execute(query)
        db.execute(delete_user_like)
        db.commit()
        return redirect(url_for("profile"))


@app.route("/like/<update_id>/<type>", methods=["GET", "POST"])
def like_post(update_id, type):
    if type == "Wifi":
        query = user_liked_post.select().where(
            (user_liked_post.c.wifi_update_id == update_id)
            & (user_liked_post.c.user_id == current_user.id)
        )
        row = db.execute(query).fetchone()
        if row:
            delete_like = likes.delete().where(
                (likes.c.wifi_id == update_id) & (likes.c.user_id == current_user.id)
            )
            delete_user_like = user_liked_post.delete().where(
                (user_liked_post.c.wifi_update_id == update_id)
                & (user_liked_post.c.user_id == current_user.id)
            )

            db.execute(delete_like)
            db.execute(delete_user_like)
            db.commit()
            return redirect(url_for("home"))

        else:
            insert_like = likes.insert().values(
                wifi_id=update_id, user_id=current_user.id
            )
            insert_user_likes = user_liked_post.insert().values(
                user_id=current_user.id, wifi_update_id=update_id
            )
            db.execute(insert_like)
            db.execute(insert_user_likes)
            db.commit()
            return redirect(url_for("home"))
    else:
        query = user_liked_post.select().where(
            (user_liked_post.c.hangout_update_id == update_id)
            & (user_liked_post.c.user_id == current_user.id)
        )
        row = db.execute(query).fetchone()
        if row:
            delete_like = likes.delete().where(
                (likes.c.hangout_id == update_id) & (likes.c.user_id == current_user.id)
            )
            delete_user_like = user_liked_post.delete().where(
                (user_liked_post.c.hangout_update_id == update_id)
                & (user_liked_post.c.user_id == current_user.id)
            )

            db.execute(delete_like)
            db.execute(delete_user_like)
            db.commit()
            return redirect(url_for("home"))

        else:
            insert_like = likes.insert().values(
                hangout_id=update_id, user_id=current_user.id
            )
            insert_user_likes = user_liked_post.insert().values(
                user_id=current_user.id, hangout_update_id=update_id
            )
            db.execute(insert_like)
            db.execute(insert_user_likes)
            db.commit()
            return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
