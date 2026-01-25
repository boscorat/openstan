# importing sqlite3 module
import sqlite3
from pathlib import Path

from PyQt6.QtSql import QSqlQuery

PATH_DB = Path(__file__).parent.joinpath("gui_db.db").as_posix()
DATABASE = Path(PATH_DB).absolute().resolve()


def add_new_project(db, project_id, project_name, project_location, session_id):
    query = QSqlQuery(db)
    query.prepare(
        "INSERT INTO project (project_id, project_name, project_location, session_created, session_updated)"
        "SELECT :project, :projectName, :projectLocation, :sessionID, :sessionID "
        "WHERE NOT EXISTS (SELECT 1 FROM project WHERE project_id = :project)"
    )
    query.bindValue(":project", project_id)
    query.bindValue(":projectName", project_name)
    query.bindValue(":projectLocation", project_location)
    query.bindValue(":sessionID", session_id)
    query.exec()
    return query.lastError()


def add_new_user(db, user_id, session_id):
    query = QSqlQuery(db)
    query.prepare(
        "INSERT INTO user (user_id, username, session_created) "
        "SELECT :user, :user, :session "
        "WHERE NOT EXISTS (SELECT 1 FROM user WHERE user_id = :user)"
    )
    query.bindValue(":user", user_id)
    query.bindValue(":session", session_id)
    query.exec()
    return query.lastError()


def add_new_session(db, session_id, user_id):
    query = QSqlQuery(db)
    query.prepare(
        "INSERT INTO session (session_id, user_id, session_datetime)"
        "SELECT :session, :user, datetime() "
        "WHERE NOT EXISTS (SELECT 1 FROM session WHERE session_id = :session)"
    )
    query.bindValue(":session", session_id)
    query.bindValue(":user", user_id)
    query.exec()
    return query.lastError()


def list_tables():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    connection.close()
    return tables


print(list_tables())
