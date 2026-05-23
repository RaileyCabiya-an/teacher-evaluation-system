from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, F
import json
from .forms import (
    LoginForm,
    StudentCreateForm,
    InstructorCreateForm,
    StudentFirstLoginForm,
    InstructorFirstLoginForm,
    StudentUpdateForm,
    InstructorUpdateForm,
)
from .models import User
from evaluation.models import Evaluation, EvaluationPeriod
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator

def no_cache(view_func): # prevent caching 
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    return wrapper

# LOGIN
def user_login(request):

    form = LoginForm(request, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():

        email = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')

        user = authenticate(request, username=email, password=password)

        if user:

            login(request, user)

            # FORCE UPDATE ONLY FOR STUDENTS & INSTRUCTORS
            if user.must_change_password and user.role in ['student', 'instructor']:
                return redirect('force_update')

            return redirect_user_by_role(user)

    return render(request, 'users/login.html', {'form': form})


def redirect_user_by_role(user):

    if user.role == 'admin':
        return redirect('admin_dashboard')

    elif user.role == 'student':
        return redirect('student_dashboard')

    elif user.role == 'instructor':
        return redirect('instructor_dashboard')

    # SAFE FALLBACK
    return redirect('login')

def redirect_user_by_role(user):

    if user.role == 'admin':
        return redirect('admin_dashboard')

    elif user.role == 'student':
        return redirect('student_dashboard')

    elif user.role == 'instructor':
        return redirect('instructor_dashboard')

    return redirect('login')

@login_required
def force_update(request):

    user = request.user

    # 🚫 BLOCK ADMIN FROM FORCE UPDATE PAGE
    if user.role == 'admin':
        return redirect('admin_dashboard')

    # If user already updated password, redirect to dashboard
    if not user.must_change_password:

        if user.role == 'student':
            return redirect('student_dashboard')

        elif user.role == 'instructor':
            return redirect('instructor_dashboard')

        return redirect('login')

    # Choose correct form based on role
    if user.role == 'student':
        form_class = StudentFirstLoginForm
    else:
        form_class = InstructorFirstLoginForm

    form = form_class(request.POST or None, instance=user)

    if request.method == 'POST':

        if form.is_valid():

            updated_user = form.save()

            # Keep user session active after password change
            update_session_auth_hash(request, updated_user)

            # Mark password as updated
            updated_user.must_change_password = False
            updated_user.save()

            # Redirect after update
            if user.role == 'student':
                return redirect('student_dashboard')

            elif user.role == 'instructor':
                return redirect('instructor_dashboard')

            return redirect('login')

    return render(
        request,
        'users/force_update.html',
        {'form': form}
    )

# ADMIN DASHBOARD
@login_required
@no_cache
def admin_dashboard(request):

    if request.user.role != 'admin':
        return redirect('login')

    teachers = User.objects.filter(role='instructor')
    students = User.objects.filter(role='student')

    total_instructors = teachers.count()
    total_students = students.count()
    total_users = total_instructors + total_students
    total_evaluations = Evaluation.objects.count()

    data = []

    for teacher in teachers:

        evaluations = Evaluation.objects.filter(teacher=teacher)

        avg = evaluations.aggregate(
            teaching=Avg('teaching_effectiveness'),
            communication=Avg('communication_skills'),
            classroom=Avg('classroom_management'),
            punctuality=Avg('punctuality'),
            engagement=Avg('student_engagement')
        )

        total_teacher_evaluations = evaluations.count()

        overall = round(
            (
                (avg['teaching'] or 0) +
                (avg['communication'] or 0) +
                (avg['classroom'] or 0) +
                (avg['punctuality'] or 0) +
                (avg['engagement'] or 0)
            ) / 5,
            2
        )

        data.append({
            'teacher': teacher,
            'avg': avg,
            'overall': overall,
            'evaluation_count': total_teacher_evaluations
        })

    # SORT BEST TEACHERS
    ranked_teachers = sorted(
        data,
        key=lambda x: (
            x['overall'],
            x['evaluation_count']
        ),
        reverse=True
    )

    # BEST TEACHER
    best_teacher = ranked_teachers[0] if ranked_teachers else None

    # CHART DATA
    chart_data = []

    for i, item in enumerate(data):

        chart_data.append({
            "id": f"chart{i+1}",
            "values": [
                round(item['avg']['teaching'] or 0, 2),
                round(item['avg']['communication'] or 0, 2),
                round(item['avg']['classroom'] or 0, 2),
                round(item['avg']['punctuality'] or 0, 2),
                round(item['avg']['engagement'] or 0, 2),
            ]
        })

    return render(request, 'users/admin_dashboard.html', {

        'data': ranked_teachers,
        'chart_data': json.dumps(chart_data),

        'total_users': total_users,
        'total_instructors': total_instructors,
        'total_students': total_students,
        'total_evaluations': total_evaluations,

        'best_teacher': best_teacher,
    })

# CREATE STUDENT
@login_required
@no_cache
def create_student(request):
    if request.user.role != 'admin':
        return redirect('login')

    form = StudentCreateForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('create_student')

    students = User.objects.filter(role='student')

    return render(request, 'users/create_student.html', {
        'form': form,
        'students': students
    })

# CREATE INSTRUCTOR
@login_required
@no_cache
def create_instructor(request):

    if request.user.role != 'admin':
        return redirect('login')

    form = InstructorCreateForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, "Instructor created successfully!")
            return redirect('create_instructor')
        else:
            print(form.errors)  # DEBUG (REMOVE LATER)

    instructors = User.objects.filter(role='instructor')

    return render(request, 'users/create_instructor.html', {
        'form': form,
        'instructors': instructors
    })

@login_required
@no_cache
def student_dashboard(request):

    if request.user.role != 'student':
        return redirect('login')

    active_period = EvaluationPeriod.objects.filter(is_active=True).first()

    if not active_period:
        return render(request, 'users/student_dashboard.html', {
            'active_period': None,
            'evaluated_teachers': [],
            'pending_teachers': []
        })

    evaluations = Evaluation.objects.filter(
        student=request.user,
        period=active_period
    )

    evaluated_ids = set(evaluations.values_list('teacher_id', flat=True))

    teachers = User.objects.filter(role='instructor')

    teacher_list = [
        {
            'teacher': t,
            'is_evaluated': t.id in evaluated_ids
        }
        for t in teachers
    ]

    pending_teachers = [t for t in teacher_list if not t['is_evaluated']]
    evaluated_teachers = [t for t in teacher_list if t['is_evaluated']]

    return render(request, 'users/student_dashboard.html', {
        'active_period': active_period,
        'pending_teachers': pending_teachers,
        'evaluated_teachers': evaluated_teachers,
    })

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Avg, Count
from evaluation.models import Evaluation, EvaluationPeriod


@login_required
@no_cache
def instructor_dashboard(request):

    if request.user.role != 'instructor':
        return redirect('login')

    instructor = request.user

    # ─────────────────────────────────────────────
    # 1. ACTIVE TAB  (persists across filter submits)
    #    The hidden <input name="tab" value="results"> in the filter
    #    form keeps the user on the Results tab after filtering.
    # ─────────────────────────────────────────────
    active_tab = request.GET.get('tab', 'dashboard')

    # ─────────────────────────────────────────────
    # 2. FILTERS  (only meaningful on Results tab)
    # ─────────────────────────────────────────────
    selected_school_year = request.GET.get('school_year', '')
    selected_semester    = request.GET.get('semester', '')
    selected_term        = request.GET.get('term', '')

    # ─────────────────────────────────────────────
    # 3. BASE QUERYSET  — all evaluations for this instructor
    # ─────────────────────────────────────────────
    evaluations = Evaluation.objects.filter(teacher=instructor)

    # Apply filters when present
    if selected_school_year:
        evaluations = evaluations.filter(period__school_year=selected_school_year)
    if selected_semester:
        evaluations = evaluations.filter(period__semester=selected_semester)
    if selected_term:
        evaluations = evaluations.filter(period__term=selected_term)

    # ─────────────────────────────────────────────
    # 4. CURRENT ACTIVE PERIOD
    # ─────────────────────────────────────────────
    current_period = EvaluationPeriod.objects.filter(is_active=True).first()

    # ─────────────────────────────────────────────
    # 5. CATEGORY AVERAGES  (respects filters)
    # ─────────────────────────────────────────────
    category_data = evaluations.aggregate(
        teaching=Avg('teaching_effectiveness'),
        communication=Avg('communication_skills'),
        management=Avg('classroom_management'),
        punctuality=Avg('punctuality'),
        engagement=Avg('student_engagement'),
    )

    category_averages = {
        "Teaching Effectiveness": round(category_data['teaching']      or 0, 2),
        "Communication Skills":   round(category_data['communication'] or 0, 2),
        "Classroom Management":   round(category_data['management']    or 0, 2),
        "Punctuality":            round(category_data['punctuality']   or 0, 2),
        "Student Engagement":     round(category_data['engagement']    or 0, 2),
    }

    overall_average  = round(sum(category_averages.values()) / 5, 2) if evaluations.exists() else 0
    total_responses  = evaluations.count()

    # ─────────────────────────────────────────────
    # 6. CATEGORY CHART DATA
    # ─────────────────────────────────────────────
    chart_data = {
        "labels": list(category_averages.keys()),
        "values": list(category_averages.values()),
    }

    # ─────────────────────────────────────────────
    # 7. TREND DATA  — one point per period (all time, unfiltered)
    #    Uses ALL periods so the line graph is always meaningful.
    # ─────────────────────────────────────────────
    trend_labels = []
    trend_values = []

    all_instructor_periods = (
        EvaluationPeriod.objects
        .filter(evaluations__teacher=instructor)
        .distinct()
        .order_by('school_year', 'semester', 'term')
    )

    for period in all_instructor_periods:
        qs = Evaluation.objects.filter(teacher=instructor, period=period)
        agg = qs.aggregate(
            teaching=Avg('teaching_effectiveness'),
            communication=Avg('communication_skills'),
            management=Avg('classroom_management'),
            punctuality=Avg('punctuality'),
            engagement=Avg('student_engagement'),
        )
        avg_score = round(
            (
                (agg['teaching']      or 0) +
                (agg['communication'] or 0) +
                (agg['management']    or 0) +
                (agg['punctuality']   or 0) +
                (agg['engagement']    or 0)
            ) / 5,
            2
        )
        trend_labels.append(
            f"{period.school_year} {period.get_semester_display()} {period.get_term_display()}"
        )
        trend_values.append(avg_score)

    chart_trend = {
        "labels": trend_labels,
        "values": trend_values,
    }

    # ─────────────────────────────────────────────
    # 8. PERFORMANCE INDICATOR
    # ─────────────────────────────────────────────
    if len(trend_values) >= 2:
        latest   = trend_values[-1]
        previous = trend_values[-2]
        diff     = round(latest - previous, 2)

        if latest > previous:
            performance_status = f"Performance Improved (+{diff})"
            performance_icon   = "bi-graph-up-arrow"
        elif latest < previous:
            performance_status = f"Performance Declined ({diff})"
            performance_icon   = "bi-graph-down-arrow"
        else:
            performance_status = "Performance Stable"
            performance_icon   = "bi-dash-circle"
    else:
        performance_status = "Not Enough Data Yet"
        performance_icon   = "bi-dash-circle"

    # ─────────────────────────────────────────────
    # 9. FILTER DROPDOWN OPTIONS
    # ─────────────────────────────────────────────
    school_years = (
        EvaluationPeriod.objects
        .values_list('school_year', flat=True)
        .distinct()
        .order_by('school_year')
    )

    return render(request, "users/instructor_dashboard.html", {
        # Tab state
        "active_tab":           active_tab,

        # Period
        "current_period":       current_period,

        # Stats
        "category_averages":    category_averages,
        "overall_average":      overall_average,
        "total_responses":      total_responses,

        # Chart JSON (read by js via json_script)
        "chart_data":           chart_data,
        "chart_trend":          chart_trend,

        # Performance indicator
        "performance_status":   performance_status,
        "performance_icon":     performance_icon,

        # Filter state
        "school_years":         school_years,
        "selected_school_year": selected_school_year,
        "selected_semester":    selected_semester,
        "selected_term":        selected_term,
    })

@login_required
@no_cache
def update_student(request, pk):
    if request.user.role != 'admin':
        return redirect('login')

    student = get_object_or_404(User, pk=pk, role='student')

    form = StudentUpdateForm(request.POST or None, instance=student)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Student updated successfully!")
        return redirect('create_student')

    return render(request, 'users/update_student.html', {
        'form': form,
        'student': student
    })

@login_required
@no_cache
def delete_student(request, pk):
    if request.user.role != 'admin':
        return redirect('login')

    student = get_object_or_404(User, pk=pk, role='student')

    if request.method == 'POST':
        student.delete()
        messages.success(request, "Student deleted successfully!")

    return redirect('create_student')

@login_required
@no_cache
def chart_api(request):

    if request.user.role != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    teachers = User.objects.filter(role='instructor')

    chart_data = []

    for i, teacher in enumerate(teachers):

        avg = Evaluation.objects.filter(
            teacher=teacher
        ).aggregate(
            teaching=Avg('teaching_effectiveness'),
            communication=Avg('communication_skills'),
            classroom=Avg('classroom_management'),
            punctuality=Avg('punctuality'),
            engagement=Avg('student_engagement')
        )

        chart_data.append({
            "id": f"chart{i+1}",
            "values": [
                round(avg['teaching'] or 0, 2),
                round(avg['communication'] or 0, 2),
                round(avg['classroom'] or 0, 2),
                round(avg['punctuality'] or 0, 2),
                round(avg['engagement'] or 0, 2)
            ]
        })

    return JsonResponse(chart_data, safe=False)

@login_required
@no_cache
def update_instructor(request, pk):
    if request.user.role != 'admin':
        return redirect('login')

    instructor = get_object_or_404(User, pk=pk, role='instructor')

    if request.method == 'POST':
        form = InstructorUpdateForm(request.POST, instance=instructor)

        if form.is_valid():
            form.save()
            messages.success(request, "Instructor updated successfully.")
            return redirect('create_instructor')
    else:
        form = InstructorUpdateForm(instance=instructor)

    return render(request, 'users/instructor_update.html', {
        'form': form
    })

@login_required
@no_cache
def delete_instructor(request, pk):
    if request.user.role != 'admin':
        return redirect('login')

    instructor = get_object_or_404(User, pk=pk, role='instructor')

    if request.method == 'POST':
        instructor.delete()
        messages.success(request, "Instructor deleted successfully.")
        return redirect('create_instructor')

    return redirect('create_instructor')

@login_required
@no_cache
def student_update_profile(request):

    if request.method == "POST":

        request.user.first_name = request.POST.get("first_name")
        request.user.last_name = request.POST.get("last_name")
        request.user.email = request.POST.get("email")

        request.user.save()

        messages.success(request, "Profile updated successfully.")

    return redirect("student_dashboard")

@login_required
@no_cache
def instructor_update_profile(request):
    if request.method == "POST":
        request.user.first_name = request.POST.get("first_name")
        request.user.last_name  = request.POST.get("last_name")
        request.user.email      = request.POST.get("email")
        request.user.save()
        messages.success(request, "Profile updated successfully.")
    return redirect("instructor_dashboard")

