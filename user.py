from flask_login import UserMixin

from db import get_db


class User(UserMixin):
    def __init__(self, id_, name, email, profile_pic):
        self.id = id_
        self.name = name
        self.email = email
        self.profile_pic = profile_pic

    @staticmethod
    def get(user_id):
        db = get_db()
        user = db.execute(
            "SELECT * FROM user WHERE id = ?", (user_id,)
        ).fetchone()
        if not user:
            return None

        user = User(
            id_=user[0], name=user[1], email=user[2], profile_pic=user[3]
        )
        return user

    @staticmethod
    def create(id_, name, email, profile_pic):
        db = get_db()
        db.execute(
            "INSERT INTO user (id, name, email, profile_pic) "
            "VALUES (?, ?, ?, ?)",
            (id_, name, email, profile_pic),
        )
        db.commit()


class Recording:
    def __init__(self, file, room_num, rec_date, rec_time, json):
        self.file = file
        self.room = room_num
        self.rec_date = rec_date
        self.rec_time = rec_time
        self.json = json

    @staticmethod
    def get(room_num, rec_date, rec_time):
        db = get_db()
        recording = db.execute(
            "SELECT * FROM recording WHERE room = ? AND rec_date = ? AND rec_time = ?", (room_num, rec_date, rec_time)
        ).fetchone()
        if not recording:
            return None

        recording = Recording(
            file=recording[0], room_num=recording[1], rec_date=recording[2], rec_time=recording[3], json=recording[4]
        )
        return recording

    @staticmethod
    def create(file, room_num, rec_date, rec_time, json):
        db = get_db()
        db.execute(
            "INSERT INTO recording (file, room_num, rec_date, rec_time, json) "
            "VALUES (?, ?, ?, ?, ?)",
            (file, room_num, rec_date, rec_time, json),
        )
        db.commit()


