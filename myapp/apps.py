def ready(self):
    """Ensure user roles and permissions exist when the app starts, and assign roles to users."""
    from django.db import connection

    with connection.cursor() as cursor:
        # Ensure the "Admin", "Moderator", and "User" groups exist
        cursor.execute("""
            INSERT INTO auth_group (name) 
            VALUES ('Admin'), ('Moderator'), ('User')
            ON CONFLICT (name) DO NOTHING;
        """)

        # Assign default permissions to groups
        roles_permissions = {
            "Admin": ["add_user", "change_user", "delete_user", "view_user"],
            "Moderator": ["change_user", "view_user"],
            "User": ["view_user"],
        }

        for role, perms in roles_permissions.items():
            for perm in perms:
                cursor.execute("""
                    INSERT INTO auth_permission (codename, content_type_id, name)
                    SELECT %s, (SELECT id FROM django_content_type WHERE model = 'user' LIMIT 1), %s
                    ON CONFLICT (codename, content_type_id) DO NOTHING;
                """, [perm, f'Can {perm.replace("_", " ")}'])

                cursor.execute("""
                    INSERT INTO auth_group_permissions (group_id, permission_id)
                    SELECT g.id, p.id FROM auth_group g, auth_permission p
                    WHERE g.name = %s AND p.codename = %s
                    ON CONFLICT (group_id, permission_id) DO NOTHING;
                """, [role, perm])

        # Fetch group IDs
        cursor.execute("SELECT id FROM auth_group WHERE name='Admin'")
        admin_group_id = cursor.fetchone()
        admin_group_id = admin_group_id[0] if admin_group_id else None

        cursor.execute("SELECT id FROM auth_group WHERE name='Moderator'")
        moderator_group_id = cursor.fetchone()
        moderator_group_id = moderator_group_id[0] if moderator_group_id else None

        cursor.execute("SELECT id FROM auth_group WHERE name='User'")
        user_group_id = cursor.fetchone()
        user_group_id = user_group_id[0] if user_group_id else None

        # Debugging logs
        print(f"Admin Group ID: {admin_group_id}")
        print(f"Moderator Group ID: {moderator_group_id}")
        print(f"User Group ID: {user_group_id}")

        # Assign superusers to the "Admin" group
        if admin_group_id:
            cursor.execute("""
                INSERT INTO auth_user_groups (user_id, group_id)
                SELECT id, %s FROM auth_user 
                WHERE is_superuser=TRUE 
                AND id NOT IN (SELECT user_id FROM auth_user_groups WHERE group_id=%s)
            """, [admin_group_id, admin_group_id])

        # Assign regular users to "User" group if they have no role
        if user_group_id:
            cursor.execute("""
                INSERT INTO auth_user_groups (user_id, group_id)
                SELECT id, %s FROM auth_user 
                WHERE is_superuser=FALSE 
                AND id NOT IN (SELECT user_id FROM auth_user_groups)
            """, [user_group_id])

        # Verify role assignments
        cursor.execute("SELECT user_id, group_id FROM auth_user_groups")
        assigned_roles = cursor.fetchall()
        print(f"Assigned Roles: {assigned_roles}")
