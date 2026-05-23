from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.user_login, name='login'),

    path('force-update/', views.force_update, name='force_update'),

    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('create-student/', views.create_student, name='create_student'),
    path('create-instructor/', views.create_instructor, name='create_instructor'),

    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('instructor-dashboard/', views.instructor_dashboard, name='instructor_dashboard'),

    path('students/update/<int:pk>/', views.update_student, name='update_student'),
    path('update-instructor/<int:pk>/', views.update_instructor, name='update_instructor'),
    path('students/delete/<int:pk>/', views.delete_student, name='delete_student'),
    path('delete-instructor/<int:pk>/', views.delete_instructor, name='delete_instructor'),
    path('api/charts/', views.chart_api, name='chart_api'),

    path(
        'student/update-profile/',
        views.student_update_profile,
        name='student_update_profile'
    ),
    path("instructor/instructor_update_profile/", views.instructor_update_profile, name="faculty_update_profile"),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]