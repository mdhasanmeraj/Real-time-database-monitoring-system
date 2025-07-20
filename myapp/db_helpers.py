from django.db import connection


def setup_roles_table():
    """Ensure the user_roles table exists."""
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id INTEGER PRIMARY KEY,
                role TEXT CHECK(role IN ('Admin', 'Moderator', 'User')) NOT NULL
            )
        """)


def assign_roles():
    """Fetch users from auth_user and assign roles dynamically."""
    with connection.cursor() as cursor:
        # Ensure the table exists
        setup_roles_table()

        # Delete existing user roles to avoid duplicates
        cursor.execute("DELETE FROM user_roles")

        # Fetch users and assign roles based on their permissions
        cursor.execute("""
            INSERT INTO user_roles (user_id, role)
            SELECT 
                id,
                CASE 
                    WHEN is_superuser = 1 THEN 'Admin'
                    WHEN is_staff = 1 THEN 'Moderator'
                    ELSE 'User'
                END
            FROM auth_user
        """)


def fetch_users_with_roles():
    """Retrieve all users with their assigned roles."""
    assign_roles()  # Ensure roles are up to date

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                au.id, au.username, au.email, 
                COALESCE(ur.role, 'User') AS role
            FROM auth_user au
            LEFT JOIN user_roles ur ON au.id = ur.user_id
            ORDER BY au.id;
        """)
        users = cursor.fetchall()

    return [
        {"id": user[0], "username": user[1], "email": user[2], "role": user[3]}
        for user in users
    ]
