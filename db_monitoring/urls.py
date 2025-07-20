"""
URL configuration for db_monitoring project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from myapp import views  # Correctly import views from your app
from django.urls import path
from myapp.views import admin_dashboard, change_user_role, create_user
from django.urls import path
#from .views import user_management, delete_user, update_user_permissions
from myapp.views import vacuum_table
from django.shortcuts import redirect  # For redirecting the root path


urlpatterns = [
    path('admin/', admin.site.urls),
    path("", lambda request: redirect("index/")),  # Redirect root to index page
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('login/', auth_views.LoginView.as_view(template_name='myapp/login.html'), name='login'),
    path('index/', views.index, name='index'),
    
    path('index_resource/', views.index_resource, name='index_resource'),
    path('cpu_usage_grid/', views.cpu_usage_grid, name='cpu_usage_grid'),
    path('restart-db/', views.restart_database, name='restart_database'), 
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('register/', views.RegisterUser, name="register"),
    path("vacuum-table/", vacuum_table, name="vacuum_table"),
    path('change-role/<int:user_id>/', views.change_user_role, name='change_user_role'),
     path('delete_user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('create-user/', views.create_user, name='create_user'),
    
    path('archive_table/', views.archive_table, name='archive_table'),
    
]

    
    # path('user_management/',  views.user_management, name='user_management'),
    # path('delete_user/<int:user_id>/',  views.delete_user, name='delete_user'),
    # path('add_user/', add_user, name='add_user'), 
    # path('update_user_permissions/',  views.update_user_permissions, name='update_user_permissions'),
