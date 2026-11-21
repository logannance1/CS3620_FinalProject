from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

# Create your views here.
def logout_view(request):
    logout(request)
    return redirect('login')

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next = request.GET.get("next") or "dashboard"
            return redirect(next)
    else:
        form = AuthenticationForm()

    return render(request, "users/login.html", { "form": form })

def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)

        if form.is_valid():
            form.save()
            username = form.cleaned_data.get("username")
            messages.success(request, f"{username} account created!")
            return redirect("login")
    else:
        form = UserCreationForm()
    
    return render(request, "users/register.html", { "form": form })