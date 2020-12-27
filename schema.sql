CREATE TABLE user (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  profile_pic TEXT NOT NULL
);

CREATE TABLE recording (
  file TEXT PRIMARY KEY,
  room_num TEXT NOT NULL,
  rec_date TEXT NOT NULL,
  rec_time TEXT NOT NULL,
  json TEXT NOT NULL
);

--CREATE TABLE room (
--  room_num TEXT PRIMARY KEY,
--  google_folder TEXT UNIQUE NOT NULL,
--  tag TEXT NOT NULL
--);
--
--CREATE TABLE face (
--  id TEXT PRIMARY KEY,
--  encoding TEXT NOT NULL,
--  name TEXT
--  first_pic TEXT NOT NULL
--);
