
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from staticApp.models import Users
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from datetime import datetime
from staticApp.models import Profile
from django.contrib.auth.hashers import make_password

# Create your views here.
def login(request):
    if request.method == "POST":
        username = request.POST["username"].strip()
        password = request.POST["password"]

        user = authenticate(username= username, password=password)

        if user is not None:
            auth_login(request, user)
            messages.success(request, 'Login successful!')
            return redirect("index")
        else:
            messages.info(request,'invalid credentials')
            return redirect("login")

    else:
        return render(request, 'login.html')


def register(request):
    if request.method == "POST":
        firstname = request.POST["fname"]
        lastname = request.POST["lname"]
        username = request.POST["username"]
        email = request.POST["email"]
        password1 = request.POST["password"]
        password2 = request.POST["confarm_pass"]

        # Validate passwords
        if password1 != password2:
            messages.error(request, "❌ Passwords do not match")
            return redirect('register')

        # Check for duplicates
        if Users.objects.filter(username=username).exists():
            messages.error(request, "❌ Username already exists, please choose another one")
            return redirect('register')

        if Users.objects.filter(email=email).exists():
            messages.error(request, "❌ Email is already registered")
            return redirect('register')

        # Create user
        user = Users.objects.create_user(
            username=username,
            password=password1,
            email=email,
            first_name=firstname,
            last_name=lastname
        )
        user.save()

        Profile.objects.create(user=user)

        # 📨 Send welcome email
        try:
            subject = "🎉 Welcome to FoodBeverage!"
            context = {
                'name': firstname,
                'year': datetime.now().year,
            }

            html_content = render_to_string('welcome_email.html', context)
            text_content = strip_tags(html_content)

            email_message = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [email]  # Send to the user's email
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send(fail_silently=False)

        except Exception as e:
            print(f"Email send error: {e}")

            # 📨 Send notification email to the ADMIN
            try:
                admin_subject = f"🧾 New User Registered: {firstname} {lastname}"
                admin_context = {
                    'firstname': firstname,
                    'lastname': lastname,
                    'email': email,
                    'username': username,
                    'year': datetime.now().year,
                }
                admin_html = render_to_string('admin_notify_email.html', admin_context)
                admin_text = strip_tags(admin_html)

                admin_email = EmailMultiAlternatives(
                    admin_subject,
                    admin_text,
                    settings.DEFAULT_FROM_EMAIL,
                    ["walepython@gmail.com"]
                )
                admin_email.attach_alternative(admin_html, "text/html")
                admin_email.send(fail_silently=False)

            except Exception as e:
                print(f"Admin email error: {e}")

        messages.success(request, "✅ Account created! Welcome email sent. You can now login.")
        return redirect('login')

    return render(request, 'register.html')

def logout(request):
    auth_logout(request)
    return redirect("login")
