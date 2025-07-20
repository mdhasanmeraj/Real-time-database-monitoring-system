import csv
import json
import logging
import re
import subprocess
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import (
    login_required,
    user_passes_test,
)
from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db import connection, IntegrityError, transaction
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt


logger = logging.getLogger(__name__)


@login_required
def admin_dashboard(request):
    """Admin dashboard displaying all users with their roles and permissions."""
    
    # Ensure required groups exist
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO auth_group (name) VALUES ('Admin')
            ON CONFLICT (name) DO NOTHING
        """)
        cursor.execute("""
            INSERT INTO auth_group (name) VALUES ('Moderator')
            ON CONFLICT (name) DO NOTHING
        """)
        cursor.execute("""
            INSERT INTO auth_group (name) VALUES ('User')
            ON CONFLICT (name) DO NOTHING
        """)

    # Fetch users along with their assigned roles using raw SQL
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                au.id, au.username, au.email, 
                COALESCE(ag.name, 'No Role Assigned') AS role
            FROM auth_user au
            LEFT JOIN auth_user_groups aug ON au.id = aug.user_id
            LEFT JOIN auth_group ag ON aug.group_id = ag.id
            ORDER BY au.id;
        """)
        users_with_roles = cursor.fetchall()

    # Format data for the template
    users = [
        {"id": user[0], "username": user[1], "email": user[2], "role": user[3]}
        for user in users_with_roles
    ]

    context = {"users": users}
    return render(request, "myapp/admin_dashboard.html", context)


@login_required
def change_user_role(request, user_id):
    """Change the role of a user using raw SQL with improved security and logging."""

    # Ensure only Admins can change roles
    if not request.user.groups.filter(name='Admin').exists():
        messages.error(request, "You don't have permission to change roles.")
        return redirect('admin_dashboard')

    # Ensure the user exists
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM auth_user WHERE id = %s", [user_id])
        user_exists = cursor.fetchone()

    if not user_exists:
        messages.error(request, "User does not exist.")
        return redirect('admin_dashboard')

    if request.method == 'POST':
        new_role = request.POST.get('role')
        valid_roles = ['Admin', 'Moderator', 'User']

        # Validate selected role
        if new_role not in valid_roles:
            messages.error(request, "Invalid role selected.")
            return redirect('admin_dashboard')

        # Prevent self-downgrade from Admin to another role
        if int(user_id) == request.user.id and new_role != 'Admin':
            messages.error(request, "You cannot change your own role to a non-admin.")
            return redirect('admin_dashboard')

        try:
            with transaction.atomic():  # Ensure atomicity
                with connection.cursor() as cursor:
                    # Fetch the group ID
                    cursor.execute("SELECT id FROM auth_group WHERE name = %s", [new_role])
                    group_id = cursor.fetchone()

                    if not group_id:
                        messages.error(request, "Role does not exist.")
                        return redirect('admin_dashboard')

                    # Remove user from all groups
                    cursor.execute("DELETE FROM auth_user_groups WHERE user_id = %s", [user_id])

                    # Assign new role
                    cursor.execute("""
                        INSERT INTO auth_user_groups (user_id, group_id)
                        VALUES (%s, %s)
                    """, [user_id, group_id[0]])

            messages.success(request, f"User role updated to {new_role}.")
            return redirect('admin_dashboard')

        except Exception as e:
            logger.error(f"Error updating user role for user {user_id}: {e}")
            messages.error(request, "An error occurred while updating the role.")
            return redirect('admin_dashboard')

    return render(request, "myapp/change_user_role.html", {"user_id": user_id, "valid_roles": ['Admin', 'Moderator', 'User']})


def RegisterUser(request):
    """Handles user registration with role assignment using raw SQL queries."""

    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password1')
        password_confirm = request.POST.get('password2')
        role = request.POST.get('role')

        valid_roles = ["Admin", "Moderator", "User"]
        if role not in valid_roles:
            messages.error(request, "Invalid role selected.")
            return redirect('register')

        if password != password_confirm:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        try:
            with transaction.atomic():
                # Create the user
                user = User.objects.create_user(username=username, email=email, password=password)

                with connection.cursor() as cursor:
                    # Ensure the role exists
                    cursor.execute("INSERT OR IGNORE INTO auth_group (name) VALUES (%s)", [role])

                    # Assign the user to the role
                    cursor.execute("""
                        INSERT INTO auth_user_groups (user_id, group_id)
                        SELECT %s, id FROM auth_group WHERE name = %s
                    """, [user.id, role])

                    # Update user privileges based on role
                    if role == 'Admin':
                        cursor.execute("UPDATE auth_user SET is_staff = TRUE, is_superuser = TRUE WHERE id = %s", [user.id])
                    elif role == 'Moderator':
                        cursor.execute("UPDATE auth_user SET is_staff = TRUE WHERE id = %s", [user.id])

            messages.success(request, f"{role} registration successful!")
            return redirect('login')

        except IntegrityError as e:
            logger.error(f"Error creating user {username}: {e}")
            messages.error(request, "Error registering user. Username may already exist.")
            return redirect('register')

    return render(request, "myapp/register.html")



# @login_required
# @csrf_exempt
# def update_user_role(request, user_id):
#     if request.method == "POST":
#         user = get_object_or_404(User, id=user_id)
#         new_role = request.POST.get("role")

#         if new_role:
#             user.profile.role = new_role  # Use `user.profile.role` if `role` is stored in a related model.
#             user.save()
#             messages.success(request, f"Role updated for {user.username}")
#         else:
#             messages.error(request, "Invalid role selection.")

#     return redirect('user_management')


# @login_required
# @csrf_exempt
# def update_user_permissions(request, user_id):
#     if request.method == "POST":
#         user = get_object_or_404(User, id=user_id)
#         selected_permissions = request.POST.getlist("permissions[]")

#         if selected_permissions:
#             user.profile.permissions = selected_permissions
#             user.save()
#             messages.success(request, f"Permissions updated for {user.username}")
#         else:
#             messages.error(request, "No permissions selected.")

#     return redirect('user_management')



def create_user(request):
    """Admin can create new users and assign roles using raw SQL queries."""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO auth_user_groups (user_id, group_id)
                    SELECT %s, id FROM auth_group WHERE name = %s
                """, [user.id, role])

            messages.success(request, f"{role} '{username}' created successfully!")
            return redirect('admin_dashboard')

    return render(request, 'myapp/create_user.html')




# Configure logger
logger = logging.getLogger(__name__)

@login_required
def delete_user(request, user_id):
    """Delete a user after removing their group associations."""
    
    # Ensure only Admins can delete users
    if not request.user.groups.filter(name='Admin').exists():
        messages.error(request, "You don't have permission to delete users.")
        return redirect('admin_dashboard')

    # Prevent an Admin from deleting their own account
    if int(user_id) == request.user.id:
        messages.error(request, "You cannot delete your own account.")
        return redirect('admin_dashboard')

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                # Check if the user exists
                cursor.execute("SELECT id FROM auth_user WHERE id = %s", [user_id])
                user_exists = cursor.fetchone()

                if not user_exists:
                    messages.error(request, "User does not exist.")
                    return redirect('admin_dashboard')

                # Remove user from all groups first to prevent FK constraint errors
                cursor.execute("DELETE FROM auth_user_groups WHERE user_id = %s", [user_id])

                # Delete the user
                cursor.execute("DELETE FROM auth_user WHERE id = %s", [user_id])

        messages.success(request, "User deleted successfully.")
        return redirect('admin_dashboard')

    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        messages.error(request, "An error occurred while deleting the user.")
        return redirect('admin_dashboard')















# def vacuum_table(request, schema, table):
#     if request.method == "POST":
#         try:
#             with connection.cursor() as cursor:
#                 # Run the VACUUM command
#                 cursor.execute(f"VACUUM FULL ANALYZE {schema}.{table};")

#             # Fetch new total size after vacuum
#             with connection.cursor() as cursor:
#                 cursor.execute("""
#                     SELECT pg_size_pretty(pg_total_relation_size(%s));
#                 """, [f"{schema}.{table}"])
#                 new_total_size = cursor.fetchone()[0]  # Get new total size in human-readable format

#             # Update bloat size to 0 in the database
#             with connection.cursor() as cursor:
#                 cursor.execute("""
#                     UPDATE admin.table_bloat 
#                     SET bloat_size = 0
#                     WHERE schema_name = %s AND table_name = %s;
#                 """, [schema, table])

#             return JsonResponse({
#                 "success": True,
#                 "message": f"Vacuumed {schema}.{table}",
#                 "new_total_size": new_total_size
#             })

#         except Exception as e:
#             return JsonResponse({"success": False, "message": str(e)}, status=500)

#     return JsonResponse({"success": False, "message": "Invalid request"}, status=400)




@login_required
@csrf_exempt
def restart_database(request):

    print("The restart_database view has been called.")
    if request.method == 'POST':
        # Details for the remote server
        remote_host = "10.77.36.43"
        remote_user = "rajesh"  # Replace 'rhel_user' with the actual username
        remote_command = "sudo systemctl restart postgresql-14"

        try:
            # Execute the remote command via SSH
            command = f"ssh {remote_user}@{remote_host} '{remote_command}'"
            result = subprocess.run(command, shell=True, text=True, capture_output=True, check=True)

            # Return success message
            return JsonResponse({
                "status": "success",
                "message": "Database server restarted successfully!",
                "output": result.stdout  # Optional: Return stdout
            })
        except subprocess.CalledProcessError as e:
            # Capture error message
            return JsonResponse({
                "status": "error",
                "message": f"Failed to restart database: {e.stderr if e.stderr else str(e)}"
            })
    return JsonResponse({"status": "error", "message": "Invalid request."})


def send_notification_email(message):
    send_mail(
        subject="Database Monitoring Alert",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=["mdhasanmeraj01@gmail.com"],  # Change to your admin email
        fail_silently=False,
    )

def index(request):

    database_name = settings.DATABASES['default']['NAME']
    user_name = settings.DATABASES['default']['USER']
    port = settings.DATABASES['default']['PORT']
    

    slow_queries = []
    idle_queries = []
    table_bloat = []
    locks = []
    system_metrics = []


    with connection.cursor() as cursor:
        # Fetch slow-running queries
        cursor.execute("""
                    SELECT
            pid,
            application_name,
            query,
            TO_CHAR(pg_stat_activity.query_start AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') AS query_start,
            now() - pg_stat_activity.query_start AS query_time,
            state
        FROM pg_stat_activity
        WHERE (now() - pg_stat_activity.query_start) > interval '15 minute' 
        order by query_time desc ;
        """)
        slow_queries = cursor.fetchall()
        
        # Fetch idle queries
        cursor.execute("""
                                    SELECT 
            pid, application_name, query, TO_CHAR(pg_stat_activity.query_start AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') AS query_start, 
            now() - query_start AS idle_duration, state
                        FROM 
                            pg_stat_activity
                        WHERE 
                            state = 'idle' 
                            AND now() - query_start > interval '1 hours'
                            order by idle_duration desc;
                    """)
        idle_queries = cursor.fetchall()
        
        # Fetch table bloat size
        cursor.execute("""
            SELECT schemaname, relname, 
            pg_size_pretty(pg_total_relation_size(relid)) AS total_size, 
            pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) AS bloat_size
            FROM pg_catalog.pg_statio_all_tables
            WHERE pg_total_relation_size(relid) - pg_relation_size(relid) > 0 and schemaname='lb1adm'
            ORDER BY bloat_size DESC
            LIMIT 20;
        """)
        table_bloat = cursor.fetchall()

        cursor.execute("""
                                    SELECT 
                pg_stat_activity.pid AS process_id,
                pg_stat_activity.application_name AS application_name,
                pg_stat_activity.query AS blocked_query,
                TO_CHAR(pg_stat_activity.query_start AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') AS query_start,
                pg_locks.mode AS lock_mode,
                pg_locks.locktype AS lock_type,
                pg_class.relname AS relation_name,
                pg_stat_activity.state AS query_state
                
            FROM 
                pg_locks
            JOIN 
                pg_class ON pg_locks.relation = pg_class.oid
            JOIN 
                pg_stat_activity ON pg_locks.pid = pg_stat_activity.pid
            WHERE 
                NOT pg_locks.granted -- Only show locks that are waiting to be granted
            ORDER BY 
                pg_stat_activity.query_start ASC;
        """)
        locks = cursor.fetchall()

        cursor.execute("""
            SELECT
            schema_name,
            relname,
            pg_size_pretty(table_size) AS size,
            table_size

            FROM (
            SELECT
            pg_catalog.pg_namespace.nspname           AS schema_name,
            relname,
            pg_relation_size(pg_catalog.pg_class.oid) AS table_size
            FROM pg_catalog.pg_class
            JOIN pg_catalog.pg_namespace ON relnamespace = pg_catalog.pg_namespace.oid) t
            WHERE schema_name NOT LIKE 'pg_%' and schema_name='lb1adm'
            ORDER BY table_size DESC LIMIT 20;
        """)
        tableSize = cursor.fetchall()

        
        
        
        #  Resource Consuming Query

        cursor.execute("""
                        
                                    SELECT 
                query, 
                calls, 
                ROUND(total_exec_time::numeric / 1000, 2) AS total_time_s,  -- Total execution time in seconds, rounded to 2 decimal places
                ROUND(mean_exec_time::numeric / 1000, 2) AS avg_time_s,     -- Average execution time in seconds, rounded to 2 decimal places
                rows AS total_rows_returned,             -- Total rows returned
                ROUND((shared_blks_hit * 8)::numeric / calls, 2) AS avg_shared_blks_hit_kb,  -- Average hits in KB per call, rounded to 2 decimal places
                ROUND((shared_blks_read * 8)::numeric / calls, 2) AS avg_shared_blks_read_kb -- Average reads in KB per call, rounded to 2 decimal places
            FROM pg_stat_statements
            ORDER BY total_exec_time DESC
            LIMIT 20;

        """)
        res_cons_quer = cursor.fetchall()






        cursor.execute("""
            SELECT 
            COUNT(*) AS total_users_with_ip
            FROM 
            pg_stat_activity
            WHERE 
            client_addr IS NOT NULL;
        """)
        user_count = cursor.fetchone()[0]


        cursor.execute("""
                    SELECT 100 - (COUNT(*)::float / NULLIF((SELECT setting::float FROM pg_settings WHERE name = 'max_connections'), 0)) * 100 AS normalized_connection_load
                        FROM pg_stat_activity
                """)
        result = cursor.fetchone()

        progress_value = result[0] if result else 0  # Default to 0 if result is None



        cursor.execute("""
                    
            SELECT (SUM(blks_hit) / NULLIF((SUM(blks_read) + SUM(blks_hit)), 0)) * 100 AS normalized_cache_hit_ratio
                            FROM pg_stat_database
                """)
        result1 = cursor.fetchone()
        
        progress_value1 = result1[0] if result1 else 0  # Default to 0 if result is None



        cursor.execute("""
            SELECT NOW() - pg_postmaster_start_time() AS uptime;
            """)
        uptime = cursor.fetchone()[0]


        cursor.execute("""
          
            SELECT  TO_CHAR(pg_postmaster_start_time() AT TIME ZONE 'Asia/Kolkata', 'DD/MM/YYYY HH24:MI:SS') AS server_start_time;
            """)
        uptime_s = cursor.fetchone()[0]


        cursor.execute("""
          
            SELECT 
            CASE 
            WHEN EXTRACT(EPOCH FROM NOW() - pg_stat_database.stats_reset) > 0 THEN
            (xact_commit + xact_rollback) / EXTRACT(EPOCH FROM NOW() - pg_stat_database.stats_reset)
            ELSE 
            0
            END AS transactions_per_second
            FROM 
            pg_stat_database where datname=%s;
            """, [database_name])
        trans_per_sec = cursor.fetchone()[0]


        cursor.execute("""
          
            SELECT COUNT(*) AS total_sessions
            FROM pg_stat_activity;

            """)
        session_count = cursor.fetchone()[0]



 


        cursor.execute("""
            select version()
        """)
        pg_version = cursor.fetchone()[0]


        cursor.execute("""
            
            select start_time, end_time, duration, size, status  FROM  admin.backup_log  order by backup_id desc limit 1
        """)
        data = cursor.fetchall()
        bak=data


        cursor.execute("""
            
            SELECT 
                mount_point, 
                size, 
                used, 
                TO_CHAR(created_at, 'DD/MM/YYYY HH24:MI') AS formatted_created_at ,
                os_version
            FROM 
                admin.filesystem_usage
                order by id desc limit 1;  
        """)
        data1 = cursor.fetchall()
        file=data1


        cursor.execute("""
            
            select cpu_usage, ram_usage, cache_usage, disk_usage, cpu_load1, cpu_load5 from admin.system_metrics order by id desc limit 1;

        """)
        data2 = cursor.fetchall()
        res=data2


        processed_res = []
        for item in res:
                processed_res.append({
                'cpu_usage': float(item[0]),
                'cpu_status': float(item[0]) < 95,  # Green if less than 95

                'ram_usage': float(item[1]),
                'ram_status': float(item[1]) < 90,  # Green if less than 90

                'cache_usage': float(item[2]),
                'cache_status': float(item[2]) > 85,  # Green if less than 80

                'disk_usage': float(item[3]),
                'disk_status': float(item[3]) < 90,  # Green if less than 90

                'cpu_load_1_min': float(item[4]),
                'cpu_load_1_min_status': float(item[4]) < 10,  # Green if less than 1.5

                'cpu_load_5_min': float(item[5]),
                'cpu_load_5_min_status': float(item[5]) < 15,  # Green if less than 1.0
            })


        cursor.execute("""
            
            select soft_version, release_date, soft_type from admin.software_version where soft_type='O'
        """)
        data = cursor.fetchall()
        soft=data

        cursor.execute("""
            
            select soft_version, release_date, soft_type from admin.software_version where soft_type='D'
        """)
        data = cursor.fetchall()
        soft2=data


        cursor.execute("""
                        
                        SELECT 
                (size::decimal - LAG(size::decimal) OVER (ORDER BY start_time)) * 1024 AS size_increase_mb
            FROM admin.backup_log 
            ORDER BY backup_id DESC 
            LIMIT 1;
             """)
        dsize = cursor.fetchone()[0]


        cursor.execute("""
                        
                        select  db_start_no from admin.backup_log order by backup_id desc limit 1
             """)
        ser_start_no = cursor.fetchone()[0]
        


        cursor.execute("""
            SELECT cpu_usage, ram_usage, cache_usage, disk_usage, created_at
            FROM admin.system_metrics
            ORDER BY id DESC
            LIMIT 50;
        """)
        data = cursor.fetchall()

        system_metrics = [
            {
                'timestamp': item[4].strftime('%Y-%m-%d %H:%M:%S'),
                'cpu_usage': float(item[0]),
                'ram_usage': float(item[1]),
                'cache_usage': float(item[2]),
                'disk_usage': float(item[3])
            }
            for item in data
        ]

        





    
    

    # Calculate counts
    slow_queries_count = len(slow_queries)
    idle_queries_count = len(idle_queries)
    locks_count = len(locks)

    context = {
        'database_name': database_name,
        'user_name': user_name,
        'port' : port,
        'slow_queries': slow_queries,
        'idle_queries': idle_queries,
        'locks': locks,
        'table_bloat': table_bloat,
        'tableSize' : tableSize,
        'res_cons_quer' : res_cons_quer,
        'progress_value': progress_value,
        'progress_value1': progress_value1,
        'uptime' : uptime,
        'uptime_s' : uptime_s,
        'pg_version' : pg_version,
        'trans_per_sec': trans_per_sec,
        'session_count' : session_count,

        'slow_queries_count': slow_queries_count,
        'idle_queries_count': idle_queries_count,
        'locks_count' : locks_count,
        'user_count' : user_count,

        'system_metrics': system_metrics,  # Include system metrics data


        'message': 'Diagnos_DB',
        'bak':bak, 
        'data' : data,
        'file' : file, 
        'data1' : data1,
        'processed_res': processed_res,
        'soft':soft,
        'soft2':soft2,
        'dsize':dsize,
        'ser_start_no':ser_start_no


    }

    return render(request, "myapp/index.html", context)
    






def index_resource(request):

    with connection.cursor() as cursor:
        cursor.execute("""
            
            select TO_CHAR(created_at::timestamp, 'YYYY-MM-DD HH24:MI') as created_at, cpu_usage, ram_usage, cache_usage, disk_usage, cpu_load1, cpu_load5 
            from admin.system_metrics order by id desc ;

        """)
        data2 = cursor.fetchall()
        res=data2


    processed_res = []

    
    for item in res:
                processed_res.append({


        'created_at': item[0],  # Assuming item[0] contains the timestamp or creation date
        'cpu_usage': float(item[1]),
        'cpu_status': float(item[1]) < 95,  # Green if less than 95
        'ram_usage': float(item[2]),
        'ram_status': float(item[2]) < 90,  # Green if less than 90
        'cache_usage': float(item[3]),
        'cache_status': float(item[3]) > 85,  # Green if more than 85
        'disk_usage': float(item[4]),
        'disk_status': float(item[4]) < 90,  # Green if less than 90
        'cpu_load_1_min': float(item[5]),
        'cpu_load_1_min_status': float(item[5]) < 10,  # Green if less than 10
        'cpu_load_5_min': float(item[6]),
        'cpu_load_5_min_status': float(item[6]) < 15,  # Green if less than 15
            })


    # SQL query to check for data
    query = """
    SELECT DISTINCT A.cpu_usage, B.pid, user_name, B.cpu_usage, mem_usage, datname, state, query, query_start, 
           now() - query_start AS duration
    FROM admin.system_metrics A, admin.high_cpu_processes B, pg_stat_activity C
    WHERE TO_CHAR(A.created_at, 'YYYY:MM:DD HH24:MI') = TO_CHAR(B.recorded_at, 'YYYY:MM:DD HH24:MI')
      AND B.pid = C.pid;
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()

    # Check if results exist
    has_data = bool(results)  # True if data exists, False otherwise

    with connection.cursor() as cursor:
        cursor.execute("SELECT metric_name, metric_value, unit FROM admin.system_optimization")
        optimization_data = cursor.fetchall()

  

    
    context = {
    # Existing context data...
    'processed_res_json': json.dumps(processed_res),  # Convert Python data to JSON
    'has_data': has_data,
    "optimization_data": optimization_data
        }

    return render(request, "myapp/index_resource.html", context)




def cpu_usage_grid(request):
    # Retrieve query parameters
    timestamp = request.GET.get('timestamp')  # Example: '2024-12-23T16:30:00'
    cpu_usage = request.GET.get('cpu_usage')  # Example: '85'

    # Base SQL query
    query = """
        SELECT distinct  pid, cpu_usage, user_name, process_cpu_usage, mem_usage, state, query, query_start, duration, 
			  TO_CHAR(created_at, 'YYYY:MM:DD HH24:MI') as created_at
        FROM admin.high_cpu_process_metrics 
    """

    # Build filters and parameters for a secure query
    filter_clauses = []
    params = []

    # Add timestamp filter
    if timestamp:
        try:
            timestamp_obj = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
            filter_clauses.append("created_at = %s")
            params.append(timestamp_obj.strftime('%Y-%m-%d %H:%M:%S'))
        except ValueError:
            print("Invalid timestamp format received")

    # Add CPU usage filter
    if cpu_usage:
        try:
            cpu_usage = float(cpu_usage)
            filter_clauses.append("cpu_usage = %s")
            params.append(cpu_usage)
        except ValueError:
            print("Invalid CPU usage format received")

    # Apply filters if any
    if filter_clauses:
        query += " WHERE " + " AND ".join(filter_clauses)

    print("Final Query:", query)
    print("Parameters:", params)

    # Execute query
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

    # Convert query result into a list of dictionaries
    data = [dict(zip(columns, row)) for row in rows]

    # Prepare context for rendering
    context = {
        'data': data,  # Pass the filtered data to the template
    }

    # Render the grid_view.html template with the filtered data
    return render(request, "myapp/cpu_usage_grid.html", context)



@csrf_exempt
def vacuum_table(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            schema = data.get("schema")
            table = data.get("table")

            if not schema or not table:
                return JsonResponse({"success": False, "error": "Invalid schema or table name"})

            query = f'VACUUM ANALYZE "{schema}"."{table}";'
            
            with connection.cursor() as cursor:
                cursor.execute(query)

            return JsonResponse({"success": True, "message": f"Vacuum completed for {table}"})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method"})

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
@csrf_protect
def archive_table(request):
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            schema_name = data['schema_name']
            table_name = data['table_name']
            retention_period = int(data['retention_period'])

            with connection.cursor() as cursor:
                # Create archive table with same structure plus archive_timestamp
                archive_table_name = f"{table_name}_archive"
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {schema_name}.{archive_table_name} 
                    (LIKE {schema_name}.{table_name} INCLUDING ALL);
                    
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_schema = '{schema_name}'
                            AND table_name = '{archive_table_name}'
                            AND column_name = 'archive_timestamp'
                        ) THEN
                            EXECUTE 'ALTER TABLE {schema_name}.{archive_table_name} 
                                    ADD COLUMN archive_timestamp timestamp without time zone 
                                    DEFAULT CURRENT_TIMESTAMP';
                        END IF;
                    END;
                    $$;
                """)

                # Move all data to archive table
                cursor.execute(f"""
                    INSERT INTO {schema_name}.{archive_table_name}
                    SELECT *, CURRENT_TIMESTAMP 
                    FROM {schema_name}.{table_name};
                """)

                # Truncate original table
                cursor.execute(f"""
                    TRUNCATE TABLE {schema_name}.{table_name};
                """)

                # Create restore function
                cursor.execute(f"""
                    CREATE OR REPLACE FUNCTION {schema_name}.restore_{table_name}_data()
                    RETURNS void AS $$
                    DECLARE
                        column_list text;
                    BEGIN
                        -- Get column list excluding archive_timestamp
                        SELECT STRING_AGG(column_name, ', ')
                        INTO column_list
                        FROM information_schema.columns
                        WHERE table_schema = '{schema_name}'
                        AND table_name = '{archive_table_name}'
                        AND column_name != 'archive_timestamp';
                        
                        -- Restore data
                        EXECUTE format('
                            INSERT INTO {schema_name}.{table_name}
                            SELECT %s
                            FROM {schema_name}.{archive_table_name}
                            WHERE archive_timestamp < CURRENT_DATE - INTERVAL ''%s days''
                        ', column_list, {retention_period});
                        
                        -- Clean up archive table
                        EXECUTE format('
                            DELETE FROM {schema_name}.{archive_table_name}
                            WHERE archive_timestamp < CURRENT_DATE - INTERVAL ''%s days''
                        ', {retention_period});
                    END;
                    $$ LANGUAGE plpgsql;
                """)

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})