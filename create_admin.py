import os
import django

# ──────────────────────────────────────────────────────────────────────────────
#  1. Setup Django Environment
# ──────────────────────────────────────────────────────────────────────────────
# This allows the script to be run independently from the command line.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ghk.settings')
django.setup()

from hospital.models import CustomUser

def create_admin_user():
    """
    Automatically creates a Superuser with 'Admin' role if it doesn't already exist.
    """
    username = 'admin_kashipur'
    email = 'admin@ghk.com'
    password = 'Kashipur@2026'
    role = 'ADMIN'  # Using the constant value from CustomUser model

    print(f"Checking if user '{username}' exists...")

    if CustomUser.objects.filter(username=username).exists():
        print(f"[-] Skip: User '{username}' already exists in the database.")
        return

    try:
        print(f"[+] Creating superuser '{username}'...")
        
        # We use create_superuser to handle hashing and default superuser flags
        user = CustomUser.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )

        # 4. Profile & Roles: Ensure flags and custom fields are set
        user.role = role
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.is_approved = True  # Staff/Admin must be approved to login in this project
        user.save()

        print("─────────────────────────────────────────────────────────────────")
        print(f"Successfully created Superuser!")
        print(f"Username : {username}")
        print(f"Email    : {email}")
        print(f"Role     : {role}")
        print(f"Flags    : Superuser=True, Staff=True, Active=True, Approved=True")
        print("─────────────────────────────────────────────────────────────────")

    except Exception as e:
        print(f"[!] Error creating user: {e}")

if __name__ == '__main__':
    create_admin_user()
