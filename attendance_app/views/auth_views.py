# attendance_app/views/auth_views.py
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect

# Assuming forms.py is at the app root
from ..forms import AdminLoginForm


def admin_login_view(request):
    if request.user.is_authenticated:
        return redirect('attendance_app:admin_dashboard')

    if request.method == 'POST':
        form = AdminLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('attendance_app:admin_dashboard')
    else:
        form = AdminLoginForm(request)
    return render(request, 'attendance_app/admin_login.html', {'form': form})


def admin_logout_view(request):
    logout(request)
    return redirect('attendance_app:admin_login')
