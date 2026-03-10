"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import sqlite3

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

DB_PATH = current_dir / "activities.db"

# Seed data used when initializing an empty database
INITIAL_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


def get_connection():
    """Create a SQLite connection with row access by column name."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """Create tables and seed initial activity data if database is empty."""
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_name TEXT NOT NULL,
                email TEXT NOT NULL,
                UNIQUE(activity_name, email),
                FOREIGN KEY(activity_name) REFERENCES activities(name) ON DELETE CASCADE
            )
            """
        )

        cursor.execute("SELECT COUNT(*) AS count FROM activities")
        activity_count = cursor.fetchone()["count"]

        if activity_count == 0:
            for activity_name, details in INITIAL_ACTIVITIES.items():
                cursor.execute(
                    """
                    INSERT INTO activities (name, description, schedule, max_participants)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        activity_name,
                        details["description"],
                        details["schedule"],
                        details["max_participants"],
                    ),
                )
                for email in details["participants"]:
                    cursor.execute(
                        """
                        INSERT INTO participants (activity_name, email)
                        VALUES (?, ?)
                        """,
                        (activity_name, email),
                    )

        connection.commit()


def fetch_all_activities():
    """Return all activities in the existing API response shape."""
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM activities ORDER BY name")
        activity_rows = cursor.fetchall()

        activities = {}
        for row in activity_rows:
            cursor.execute(
                """
                SELECT email
                FROM participants
                WHERE activity_name = ?
                ORDER BY email
                """,
                (row["name"],),
            )
            participant_rows = cursor.fetchall()

            activities[row["name"]] = {
                "description": row["description"],
                "schedule": row["schedule"],
                "max_participants": row["max_participants"],
                "participants": [participant["email"] for participant in participant_rows],
            }

        return activities


@app.on_event("startup")
def startup():
    initialize_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return fetch_all_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT max_participants FROM activities WHERE name = ?",
            (activity_name,),
        )
        activity = cursor.fetchone()

        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        cursor.execute(
            "SELECT 1 FROM participants WHERE activity_name = ? AND email = ?",
            (activity_name, email),
        )
        existing_participant = cursor.fetchone()
        if existing_participant:
            raise HTTPException(status_code=400, detail="Student is already signed up")

        cursor.execute(
            "SELECT COUNT(*) AS count FROM participants WHERE activity_name = ?",
            (activity_name,),
        )
        participant_count = cursor.fetchone()["count"]

        if participant_count >= activity["max_participants"]:
            raise HTTPException(status_code=400, detail="Activity is full")

        cursor.execute(
            "INSERT INTO participants (activity_name, email) VALUES (?, ?)",
            (activity_name, email),
        )
        connection.commit()

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT 1 FROM activities WHERE name = ?",
            (activity_name,),
        )
        activity = cursor.fetchone()

        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        cursor.execute(
            "SELECT 1 FROM participants WHERE activity_name = ? AND email = ?",
            (activity_name, email),
        )
        participant = cursor.fetchone()

        if not participant:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity"
            )

        cursor.execute(
            "DELETE FROM participants WHERE activity_name = ? AND email = ?",
            (activity_name, email),
        )
        connection.commit()

    return {"message": f"Unregistered {email} from {activity_name}"}
