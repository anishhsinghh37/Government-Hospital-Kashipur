"""
setup_demo.py -- Run once to create Admin + sample data for GHK HMS.
Usage: python setup_demo.py
"""

import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ghk.settings')

import django
django.setup()

from django.utils import timezone
from hospital.models import CustomUser, DoctorProfile, Medicine, Dependent, Appointment

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=== Government Hospital Kashipur -- Demo Setup ===\n")

# 1. Admin superuser
if not CustomUser.objects.filter(username='admin').exists():
    CustomUser.objects.create_superuser(
        username='admin',
        password='admin@123',
        email='admin@ghk.gov.in',
        first_name='Hospital',
        last_name='Admin',
        role=CustomUser.ADMIN,
        is_approved=True,
    )
    print("[OK] Admin         -> admin / admin@123")
else:
    print("[--] Admin already exists, skipping.")

# 2. Doctors
doctors_data = [
    dict(username='dr_sharma',  password='doctor@123', first_name='Rajesh',  last_name='Sharma',  mobile_no='9876543210', spec='General Medicine', dept='OPD'),
    dict(username='dr_verma',   password='doctor@123', first_name='Priya',   last_name='Verma',   mobile_no='9876543211', spec='Pediatrics',       dept='Pediatrics'),
    dict(username='dr_gupta',   password='doctor@123', first_name='Anil',    last_name='Gupta',   mobile_no='9876543212', spec='Orthopaedics',     dept='Ortho'),
    dict(username='dr_mishra',  password='doctor@123', first_name='Sunita',  last_name='Mishra',  mobile_no='9876543213', spec='Gynaecology',      dept='Gynae'),
]

for d in doctors_data:
    if not CustomUser.objects.filter(username=d['username']).exists():
        user = CustomUser.objects.create_user(
            username=d['username'], password=d['password'],
            first_name=d['first_name'], last_name=d['last_name'],
            mobile_no=d['mobile_no'], role=CustomUser.DOCTOR,
            is_approved=True, is_active=True,
            email=f"{d['username']}@ghk.gov.in"
        )
        DoctorProfile.objects.create(
            user=user,
            specialization=d['spec'],
            department=d['dept'],
            available_days='MON,TUE,WED,THU,FRI',
            max_patients_per_day=30,
        )
        print(f"[OK] Doctor        -> {d['username']} / {d['password']}  ({d['spec']})")

# 3. Pharmacist
if not CustomUser.objects.filter(username='pharmacist1').exists():
    CustomUser.objects.create_user(
        username='pharmacist1', password='pharma@123',
        first_name='Suresh', last_name='Kumar',
        mobile_no='9876543220', role=CustomUser.PHARMACIST,
        is_approved=True, is_active=True,
        email='pharmacist@ghk.gov.in'
    )
    print("[OK] Pharmacist    -> pharmacist1 / pharma@123")

# 4. Receptionist
if not CustomUser.objects.filter(username='reception1').exists():
    CustomUser.objects.create_user(
        username='reception1', password='recep@123',
        first_name='Meena', last_name='Devi',
        mobile_no='9876543230', role=CustomUser.RECEPTIONIST,
        is_approved=True, is_active=True,
        email='reception@ghk.gov.in'
    )
    print("[OK] Receptionist  -> reception1 / recep@123")

# 5. Nurse
if not CustomUser.objects.filter(username='nurse1').exists():
    CustomUser.objects.create_user(
        username='nurse1', password='nurse@123',
        first_name='Anita', last_name='Singh',
        mobile_no='9876543240', role=CustomUser.NURSE,
        is_approved=True, is_active=True,
        email='nurse@ghk.gov.in'
    )
    print("[OK] Nurse         -> nurse1 / nurse@123")

# 6. Patient with Dependents (Vinod managing Himanya and Kamla Devi)
if not CustomUser.objects.filter(username='vinod_patient').exists():
    patient = CustomUser.objects.create_user(
        username='vinod_patient', password='patient@123',
        first_name='Vinod', last_name='Kumar',
        mobile_no='9876543250', role=CustomUser.PATIENT,
        is_approved=True, is_active=True,
        address='Village Kashipur, Udham Singh Nagar, Uttarakhand',
        email='vinod@example.com'
    )
    Dependent.objects.create(
        patient=patient, name='Himanya Kumar',
        dob='2018-05-15', relation='DAUGHTER', gender='F'
    )
    Dependent.objects.create(
        patient=patient, name='Kamla Devi',
        dob='1965-03-20', relation='MOTHER', gender='F'
    )
    print("[OK] Patient       -> vinod_patient / patient@123")
    print("     Dependents: Himanya Kumar (Daughter), Kamla Devi (Mother)")
else:
    print("[--] Patient vinod_patient already exists.")

# 7. Sample Medicine Inventory (10 medicines)
admin_user = CustomUser.objects.filter(username='admin').first()
medicines = [
    ('Paracetamol 500mg',   'Acetaminophen',             'PCM2024A', '2024-01-01', '2026-12-31', 500, 'TAB', 'A-1'),
    ('Amoxicillin 250mg',   'Amoxicillin',               'AMX2024B', '2024-03-01', '2025-12-31', 200, 'CAP', 'A-2'),
    ('Ibuprofen 400mg',     'Ibuprofen',                 'IBU2024C', '2024-02-01', '2026-06-30', 300, 'TAB', 'A-3'),
    ('Metformin 500mg',     'Metformin HCl',             'MET2024D', '2024-01-15', '2026-01-14', 150, 'TAB', 'B-1'),
    ('Omeprazole 20mg',     'Omeprazole',                'OMP2024E', '2024-04-01', '2025-03-31', 0,   'CAP', 'B-2'),
    ('Azithromycin 500mg',  'Azithromycin',              'AZI2024F', '2024-05-01', '2026-04-30', 100, 'TAB', 'B-3'),
    ('Cetirizine 10mg',     'Cetirizine',                'CET2024G', '2024-03-10', '2026-03-09', 8,   'TAB', 'C-1'),
    ('ORS Sachet',          'Oral Rehydration Salts',    'ORS2024H', '2024-01-01', '2026-12-31', 250, 'POW', 'C-2'),
    ('Vitamin D3 60K IU',   'Cholecalciferol',           'VD2024I',  '2024-06-01', '2025-05-31', 60,  'CAP', 'C-3'),
    ('Dolo 650',            'Paracetamol 650mg',         'DLO2024J', '2024-02-15', '2026-02-14', 400, 'TAB', 'D-1'),
]

count = 0
for (name, generic, batch, mfg, exp, qty, unit, shelf) in medicines:
    if not Medicine.objects.filter(batch_number=batch).exists():
        Medicine.objects.create(
            medicine_name=name, generic_name=generic,
            batch_number=batch, mfg_date=mfg, expiry_date=exp,
            total_quantity=qty, unit=unit,
            shelf_location=shelf, added_by=admin_user
        )
        count += 1
print(f"[OK] Medicines     -> {count} added to inventory (Omeprazole is OUT OF STOCK as demo)")

# 8. Sample today's appointment for Vinod
patient = CustomUser.objects.filter(username='vinod_patient').first()
doctor  = DoctorProfile.objects.filter(department='OPD').first()
today   = timezone.localdate()

if patient and doctor and not Appointment.objects.filter(patient=patient, date=today).exists():
    appt = Appointment.objects.create(
        patient=patient, doctor=doctor,
        date=today,
        chief_complaint='Fever and body ache since 2 days',
        status='WAITING'
    )
    print(f"[OK] Sample appt   -> Token #{appt.token_number} for Vinod with Dr. {doctor.user.get_full_name()} (OPD) today")

print("\n" + "=" * 55)
print("  SETUP COMPLETE -- Government Hospital Kashipur HMS")
print("=" * 55)
print()
print("  LOGIN CREDENTIALS:")
print("  ==================")
print("  Admin          admin          / admin@123")
print("  Doctor (4)     dr_sharma      / doctor@123")
print("  Pharmacist     pharmacist1    / pharma@123")
print("  Receptionist   reception1     / recep@123")
print("  Nurse          nurse1         / nurse@123")
print("  Patient        vinod_patient  / patient@123")
print()
print("  Start server:  python manage.py runserver")
print("  Open browser:  http://127.0.0.1:8000/")
print("  Django Admin:  http://127.0.0.1:8000/admin/")
print()
