"""
views.py — Government Hospital Kashipur
Updated with EHR, Medical History, and Patient Pharmacy Dashboards.
Includes F() based stock management and secure file uploads.
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator

from .models import (
    CustomUser, Dependent, DoctorProfile, Appointment,
    Medicine, Prescription, Feedback, StockAuditLog, MedicalRecord, PatientVitals
)
from .forms import (
    PatientRegistrationForm, StaffRegistrationForm, DependentForm,
    AppointmentForm, PrescriptionForm, MedicineForm, StockUpdateForm,
    FeedbackForm, MedicalRecordForm, DirectStaffRegistrationForm, StaffProfileUpdateForm,
    VitalsForm, LabOrderForm
)


# ═══════════════════════════════════════════════════════════
#  DECORATORS / HELPERS
# ═══════════════════════════════════════════════════════════

def role_required(*roles):
    def decorator(view_func):
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                messages.error(request, 'Access denied.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════
#  AUTHENTICATION
# ═══════════════════════════════════════════════════════════

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user:
            if not user.is_active:
                messages.error(request, 'Account deactivated.')
            elif user.is_staff_role and not user.is_approved:
                messages.warning(request, 'Pending Admin Approval.')
            else:
                login(request, user)
                user.is_available = True
                user.save(update_fields=['is_available'])
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid credentials.')
    return render(request, 'hospital/login.html')

def logout_view(request):
    if request.user.is_authenticated:
        request.user.is_available = False
        request.user.save(update_fields=['is_available'])
    logout(request)
    return redirect('login')

def register_patient(request):
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = PatientRegistrationForm()
    return render(request, 'hospital/register_patient.html', {'form': form})

def register_staff(request):
    if request.method == 'POST':
        form = StaffRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registration submitted for approval.')
            return redirect('login')
    else:
        form = StaffRegistrationForm()
    return render(request, 'hospital/register_staff.html', {'form': form})


# ═══════════════════════════════════════════════════════════
#  DASHBOARDS
# ═══════════════════════════════════════════════════════════

@login_required
def dashboard(request):
    r = request.user.role
    if r == 'ADMIN': return admin_dashboard(request)
    if r == 'DOCTOR': return doctor_dashboard(request)
    if r == 'PHARMACIST': return pharmacist_dashboard(request)
    if r == 'RECEPTIONIST': return receptionist_dashboard(request)
    if r == 'NURSE': return nurse_dashboard(request)
    return patient_dashboard(request)

@login_required
def patient_dashboard(request):
    today = timezone.localdate()
    appointments = Appointment.objects.filter(patient=request.user, date=today).select_related('doctor__user')
    all_appts = Appointment.objects.filter(patient=request.user).order_by('-date')[:5]
    dependents = Dependent.objects.filter(patient=request.user)
    context = {
        'today_appointments': appointments,
        'all_appointments': all_appts,
        'dependents': dependents,
        'today': today,
    }
    return render(request, 'hospital/dashboard/patient.html', context)

@login_required
@role_required('DOCTOR')
def doctor_dashboard(request):
    doc = getattr(request.user, 'doctor_profile', None)
    if not doc: return render(request, 'hospital/dashboard/doctor.html')
    today = timezone.localdate()
    
    # Live Queue Logic
    queue = Appointment.objects.filter(doctor=doc, date=today).order_by('token_number')
    waiting = queue.filter(status='WAITING')
    seen = queue.filter(status='COMPLETED')
    active = queue.filter(status='IN_PROGRESS').first()
    
    # Progress Bar Calculations
    total = queue.count()
    seen_count = seen.count()
    progress = (seen_count / total * 100) if total > 0 else 0
    
    context = {
        'queue': waiting[:15],  # Limit to 15 waiting patients as per requirement
        'seen_count': seen_count,
        'waiting_count': waiting.count(),
        'progress': progress,
        'active_patient': active,
        'today': today
    }
    return render(request, 'hospital/dashboard/doctor.html', context)

@login_required
@role_required('DOCTOR')
def active_consultation(request, appointment_id):
    """Dedicated page for the patient currently in the room."""
    appt = get_object_or_404(Appointment, pk=appointment_id, doctor__user=request.user)
    
    # Record Vitals
    vitals_instance = getattr(appt, 'vitals', None)
    if request.method == 'POST' and 'vitals_submit' in request.POST:
        v_form = VitalsForm(request.POST, instance=vitals_instance)
        if v_form.is_valid():
            vitals = v_form.save(commit=False)
            vitals.appointment = appt
            vitals.save()
            messages.success(request, 'Vitals recorded.')
            return redirect('active_consultation', appointment_id=appointment_id)
    else:
        v_form = VitalsForm(instance=vitals_instance)

    # Prescription Pad (Medicine dropdown handled by existing autocomplete or select)
    if request.method == 'POST' and 'prescription_submit' in request.POST:
        p_form = PrescriptionForm(request.POST)
        advice = request.POST.get('doctor_advice', '')
        if p_form.is_valid():
            with transaction.atomic():
                p = p_form.save(commit=False)
                p.appointment = appt
                p.prescribed_by = request.user
                
                # Save next visit date to appointment
                nv_date = p_form.cleaned_data.get('next_visit_date')
                if nv_date:
                    appt.next_visit_date = nv_date
                med = p.medicine
                if med.total_quantity >= p.quantity_prescribed:
                    Medicine.objects.filter(pk=med.pk).update(total_quantity=F('total_quantity') - p.quantity_prescribed)
                    p.stock_status = 'FREE_IN_STOCK'
                else: p.stock_status = 'OUT_OF_STOCK'
                p.save()
                
                # Update advice on appointment
                appt.doctor_advice = advice
                appt.save()
            messages.success(request, 'Prescription added.')
            return redirect('active_consultation', appointment_id=appointment_id)
    else:
        p_form = PrescriptionForm()

    # Lab Reports and Past History (Access restricted to this specific patient)
    lab_reports = MedicalRecord.objects.filter(patient=appt.patient, category='LAB_REPORT').order_by('-record_date')
    past_history = MedicalRecord.objects.filter(patient=appt.patient, category='PAST_HISTORY').order_by('-record_date')
    
    # Filter for dependent if applicable
    if appt.dependent:
        lab_reports = lab_reports.filter(linked_member=appt.dependent)
        past_history = past_history.filter(linked_member=appt.dependent)
    else:
        lab_reports = lab_reports.filter(linked_member__isnull=True)
        past_history = past_history.filter(linked_member__isnull=True)

    # Vitals Trends
    vitals_history = PatientVitals.objects.filter(appointment__patient=appt.patient).order_by('-recorded_at')[:10]

    context = {
        'appt': appt,
        'v_form': v_form,
        'p_form': p_form,
        'lab_reports': lab_reports,
        'past_history': past_history,
        'vitals_history': vitals_history,
        'lab_order_form': LabOrderForm(),
    }
    return render(request, 'hospital/dashboard/active_consultation.html', context)

@login_required
@role_required('DOCTOR')
def create_lab_order(request, appointment_id):
    appt = get_object_or_404(Appointment, pk=appointment_id, doctor__user=request.user)
    if request.method == 'POST':
        form = LabOrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.appointment = appt
            order.ordered_by = request.user
            order.save()
            messages.success(request, f'Lab test "{order.test_name}" requested.')
    return redirect('active_consultation', appointment_id=appointment_id)

@login_required
@role_required('DOCTOR')
def ehr_search(request):
    """Search tool for medical records of patients previously treated by this doctor."""
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        # Patients treated by this doctor
        treated_patient_ids = Appointment.objects.filter(doctor__user=request.user).values_list('patient_id', flat=True).distinct()
        results = MedicalRecord.objects.filter(
            patient_id__in=treated_patient_ids
        ).filter(
            Q(patient__first_name__icontains=query) | 
            Q(patient__last_name__icontains=query) | 
            Q(title__icontains=query)
        ).order_by('-record_date')

    return render(request, 'hospital/dashboard/ehr_search.html', {'results': results, 'query': query})

@login_required
@require_POST
def toggle_availability(request):
    """Toggle Doctor's active/on-break status."""
    request.user.is_available = not request.user.is_available
    request.user.save(update_fields=['is_available'])
    status = "Active" if request.user.is_available else "On Break"
    messages.success(request, f"Status updated to: {status}")
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def pharmacist_dashboard(request):
    low = Medicine.objects.filter(total_quantity__lte=10, is_active=True, expiry_date__gt=timezone.localdate())
    context = {'low_stock': low}
    return render(request, 'hospital/dashboard/pharmacist.html', context)

@login_required
@role_required('RECEPTIONIST', 'ADMIN')
def receptionist_dashboard(request):
    today = timezone.localdate()
    appts = Appointment.objects.filter(date=today).order_by('token_number')
    pending = CustomUser.objects.filter(is_approved=False).exclude(role='PATIENT')
    doctors = DoctorProfile.objects.all().select_related('user')
    context = {
        'today_appointments': appts, 
        'pending_approvals': pending,
        'doctors': doctors,
        'today': today
    }
    return render(request, 'hospital/dashboard/receptionist.html', context)

@login_required
def nurse_dashboard(request):
    today = timezone.localdate()
    appts = Appointment.objects.filter(date=today, status__in=['WAITING', 'IN_PROGRESS'])
    return render(request, 'hospital/dashboard/nurse.html', {'appointments': appts})

@login_required
def admin_dashboard(request):
    today = timezone.localdate()
    stats = {
        'total_patients': CustomUser.objects.filter(role='PATIENT').count(),
        'total_doctors': CustomUser.objects.filter(role='DOCTOR').count(),
        'total_appointments': Appointment.objects.filter(date=today).count(),
        'pending_staff': CustomUser.objects.filter(is_approved=False).exclude(role='PATIENT').count(),
        'open_feedbacks': Feedback.objects.filter(status='OPEN'),
        'out_of_stock': Medicine.objects.filter(total_quantity=0, is_active=True).count(),
        'staff_available': CustomUser.objects.filter(is_available=True).exclude(role='PATIENT').count(),
        'staff_offline': CustomUser.objects.filter(is_available=False).exclude(role='PATIENT').count(),
    }
    return render(request, 'hospital/dashboard/admin.html', stats)


# ═══════════════════════════════════════════════════════════
#  MEDICAL RECORDS & EHR
# ═══════════════════════════════════════════════════════════

@login_required
def ehr_dashboard(request):
    """Patient view of their own Electronic Health Records with upload modal."""
    records = MedicalRecord.objects.filter(patient=request.user).order_by('-record_date')
    lab_reports = records.filter(category='LAB_REPORT')
    
    # Handle report upload via modal (POST)
    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, request.FILES, patient=request.user)
        if form.is_valid():
            record = form.save(commit=False)
            record.patient = request.user
            record.uploaded_by = request.user
            record.save()
            messages.success(request, 'Medical report added to your EHR.')
            return redirect('ehr_dashboard')
    else:
        form = MedicalRecordForm(initial={'category': 'LAB_REPORT', 'record_date': timezone.localdate()}, patient=request.user)

    return render(request, 'hospital/reports/ehr.html', {
        'lab_reports': lab_reports,
        'all_records': records,  # Combined list for "View Lab Reports"
        'form': form
    })

@login_required
def upload_past_history(request):
    """Allow patients to upload their own archived medical history and view history."""
    past_docs = MedicalRecord.objects.filter(patient=request.user, category='PAST_HISTORY').order_by('-record_date')
    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, request.FILES, patient=request.user)
        if form.is_valid():
            record = form.save(commit=False)
            record.patient = request.user
            record.category = 'PAST_HISTORY'
            record.uploaded_by = request.user
            record.save()
            messages.success(request, 'Past history document uploaded successfully.')
            return redirect('upload_past_history')
    else:
        form = MedicalRecordForm(initial={'category': 'PAST_HISTORY', 'record_date': timezone.localdate()}, patient=request.user)
    return render(request, 'hospital/reports/upload_history.html', {
        'form': form,
        'past_docs': past_docs
    })

@login_required
def upload_report(request, appointment_id):
    """Staff/Doctor uploads lab reports linked to an appointment."""
    appointment = get_object_or_404(Appointment, pk=appointment_id)
    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, request.FILES, patient=appointment.patient)
        if form.is_valid():
            record = form.save(commit=False)
            record.patient = appointment.patient
            record.appointment = appointment
            if not record.linked_member:
                record.linked_member = appointment.dependent
            record.category = 'LAB_REPORT'
            record.uploaded_by = request.user
            record.save()
            messages.success(request, 'Lab report uploaded.')
            return redirect('appointment_detail', appointment_id=appointment_id)
    else:
        form = MedicalRecordForm(
            initial={'category': 'LAB_REPORT', 'record_date': timezone.localdate(), 'linked_member': appointment.dependent},
            patient=appointment.patient
        )
    return render(request, 'hospital/reports/upload.html', {'form': form, 'appointment': appointment})


# ═══════════════════════════════════════════════════════════
#  PHARMACY & AVAILABILITY
# ═══════════════════════════════════════════════════════════

@login_required
def medicine_availability(request):
    """Read-only searchable view for patients."""
    query = request.GET.get('q', '').strip()
    today = timezone.localdate()
    medicines = Medicine.objects.filter(is_active=True, expiry_date__gt=today).order_by('medicine_name')
    
    if len(query) >= 3:
        medicines = medicines.filter(Q(medicine_name__icontains=query) | Q(generic_name__icontains=query))
    elif query:
        messages.info(request, "Please type at least 3 letters for an accurate search.")
        medicines = Medicine.objects.none()

    paginator = Paginator(medicines, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'hospital/pharmacy/availability.html', {
        'page_obj': page_obj,
        'query': query
    })

@login_required
@role_required('PHARMACIST', 'ADMIN')
def inventory_list(request):
    medicines = Medicine.objects.all().order_by('medicine_name')
    return render(request, 'hospital/pharmacy/inventory.html', {'medicines': medicines})

@login_required
@role_required('PHARMACIST', 'ADMIN')
def add_medicine(request):
    if request.method == 'POST':
        form = MedicineForm(request.POST)
        if form.is_valid():
            med = form.save(commit=False)
            med.added_by = request.user
            med.save()
            return redirect('inventory_list')
    else:
        form = MedicineForm()
    return render(request, 'hospital/pharmacy/add_medicine.html', {'form': form})

@login_required
def update_stock(request, medicine_id):
    med = get_object_or_404(Medicine, pk=medicine_id)
    if request.method == 'POST':
        form = StockUpdateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                q = form.cleaned_data['quantity_changed']
                a = form.cleaned_data['action']
                before = med.total_quantity
                if a == 'ADD':
                    Medicine.objects.filter(pk=med.pk).update(total_quantity=F('total_quantity') + q)
                else: 
                    Medicine.objects.filter(pk=med.pk).update(total_quantity=F('total_quantity') - q)
                med.refresh_from_db()
                StockAuditLog.objects.create(
                    pharmacist=request.user, medicine=med, action=a,
                    quantity_changed=q if a == 'ADD' else -q,
                    quantity_before=before, quantity_after=med.total_quantity,
                    reason=form.cleaned_data['reason']
                )
            return redirect('inventory_list')
    else:
        form = StockUpdateForm()
    return render(request, 'hospital/pharmacy/update_stock.html', {'form': form, 'medicine': med})


# ═══════════════════════════════════════════════════════════
#  APPOINTMENTS & QUEUE
# ═══════════════════════════════════════════════════════════

@login_required
def book_appointment(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST, patient=request.user)
        if form.is_valid():
            appt = form.save(commit=False)
            appt.patient = request.user
            appt.save()
            return redirect('live_queue', appointment_id=appt.pk)
    else: form = AppointmentForm(patient=request.user)
    return render(request, 'hospital/appointments/book.html', {'form': form})

@login_required
def live_queue(request, appointment_id):
    appt = get_object_or_404(Appointment, pk=appointment_id)
    current = Appointment.objects.filter(doctor=appt.doctor, date=appt.date, status='IN_PROGRESS').first()
    ahead = Appointment.objects.filter(doctor=appt.doctor, date=appt.date, status='WAITING', token_number__lt=appt.token_number).count()
    return render(request, 'hospital/appointments/live_queue.html', {'appointment': appt, 'current_token': current, 'patients_ahead': ahead})

@login_required
def appointment_detail(request, appointment_id):
    appt = get_object_or_404(Appointment, pk=appointment_id)
    prescriptions = appt.prescriptions.all()
    records = appt.records.all()
    return render(request, 'hospital/appointments/detail.html', {'appointment': appt, 'prescriptions': prescriptions, 'records': records})

@login_required
def call_next(request):
    doc = getattr(request.user, 'doctor_profile', None)
    if not doc: return redirect('dashboard')
    today = timezone.localdate()
    Appointment.objects.filter(doctor=doc, date=today, status='IN_PROGRESS').update(status='COMPLETED')
    next_up = Appointment.objects.filter(doctor=doc, date=today, status='WAITING').order_by('token_number').first()
    if next_up:
        next_up.status = 'IN_PROGRESS'
        next_up.save()
    return redirect('doctor_queue')

@login_required
def doctor_queue(request):
    doc = getattr(request.user, 'doctor_profile', None)
    if not doc: return redirect('dashboard')
    today = timezone.localdate()
    queue = Appointment.objects.filter(doctor=doc, date=today, status__in=['WAITING', 'IN_PROGRESS']).order_by('token_number')
    return render(request, 'hospital/appointments/call_next.html', {'current': queue.filter(status='IN_PROGRESS').first(), 'waiting': queue.filter(status='WAITING')})


# ═══════════════════════════════════════════════════════════
#  FEEDBACK
# ═══════════════════════════════════════════════════════════

@login_required
def submit_feedback(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.save(commit=False)
            f.sender = request.user
            f.save()
            messages.success(request, 'Feedback submitted.')
            return redirect('dashboard')
    else: form = FeedbackForm()
    return render(request, 'hospital/feedback/submit.html', {'form': form})

@login_required
def feedback_dashboard(request):
    feedbacks = Feedback.objects.all().order_by('-created_at')
    return render(request, 'hospital/feedback/dashboard.html', {'page_obj': feedbacks})

@login_required
def feedback_inbox(request):
    """Patient view to see their own feedback history and admin replies."""
    feedbacks = Feedback.objects.filter(sender=request.user).order_by('-created_at')
    return render(request, 'hospital/feedback/inbox.html', {'feedbacks': feedbacks})

@login_required
@role_required('ADMIN', 'RECEPTIONIST')
def resolve_feedback(request, feedback_id):
    f = get_object_or_404(Feedback, pk=feedback_id)
    if request.method == 'POST':
        resp = request.POST.get('admin_response', '').strip()
        if len(resp.split()) > 200:
            messages.error(request, 'Response exceeds 200 words.')
            return redirect('feedback_dashboard')
        f.is_resolved = True
        f.status = 'RESOLVED'
        f.admin_response = resp
        f.save()
        messages.success(request, 'Reply sent and issue marked as resolved.')
    return redirect('feedback_dashboard')


# ═══════════════════════════════════════════════════════════
#  MISC
# ═══════════════════════════════════════════════════════════

@login_required
def add_dependent(request):
    if request.method == 'POST':
        form = DependentForm(request.POST)
        if form.is_valid():
            d = form.save(commit=False)
            d.patient = request.user
            d.save()
            return redirect('dashboard')
    else: form = DependentForm()
    return render(request, 'hospital/dependents/add.html', {'form': form})

@login_required
def delete_dependent(request, dep_id):
    d = get_object_or_404(Dependent, pk=dep_id, patient=request.user)
    d.delete()
    return redirect('dashboard')

@login_required
@require_GET
def medicine_autocomplete(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 3: return JsonResponse({'results': []})
    res = Medicine.objects.filter(is_active=True, medicine_name__icontains=q).values('id', 'medicine_name', 'total_quantity')[:10]
    return JsonResponse({'results': list(res)})

@login_required
@role_required('ADMIN', 'RECEPTIONIST')
def approve_staff(request, user_id):
    u = get_object_or_404(CustomUser, pk=user_id)
    u.is_approved = True
    u.is_active = True
    u.save()
    return redirect('dashboard')

@login_required
def prescribe(request, appointment_id):
    appt = get_object_or_404(Appointment, pk=appointment_id)
    if request.method == 'POST':
        form = PrescriptionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                p = form.save(commit=False)
                p.appointment = appt
                p.prescribed_by = request.user
                
                # Save next visit date to appointment
                nv_date = form.cleaned_data.get('next_visit_date')
                if nv_date:
                    appt.next_visit_date = nv_date
                    appt.save()
                med = p.medicine
                if med.total_quantity >= p.quantity_prescribed:
                    Medicine.objects.filter(pk=med.pk).update(total_quantity=F('total_quantity') - p.quantity_prescribed)
                    p.stock_status = 'FREE_IN_STOCK'
                else: p.stock_status = 'OUT_OF_STOCK'
                p.save()
            return redirect('prescribe', appointment_id=appointment_id)
    else: form = PrescriptionForm()
    return render(request, 'hospital/pharmacy/prescribe.html', {'form': form, 'appointment': appt, 'existing_prescriptions': appt.prescriptions.all()})

@login_required
def audit_log_view(request):
    logs = StockAuditLog.objects.all().order_by('-timestamp')
    return render(request, 'hospital/pharmacy/audit_log.html', {'page_obj': logs})


# ═══════════════════════════════════════════════════════════
#  STAFF & PATIENT MANAGEMENT (SUPER-ADMIN)
# ═══════════════════════════════════════════════════════════

@login_required
@role_required('ADMIN')
def staff_availability(request):
    role_filter = request.GET.get('role', '')
    staff = CustomUser.objects.exclude(role='PATIENT').order_by('role', 'first_name')
    if role_filter:
        staff = staff.filter(role=role_filter)
    return render(request, 'hospital/admin/staff_availability.html', {'staff_list': staff, 'role_filter': role_filter})

@login_required
@role_required('ADMIN', 'RECEPTIONIST')
def all_patient_records(request):
    query = request.GET.get('q', '').strip()
    patients = CustomUser.objects.filter(role='PATIENT').order_by('-date_joined')
    if query:
        patients = patients.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(username__icontains=query) | Q(id__icontains=query))
    
    paginator = Paginator(patients, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'hospital/admin/patient_list.html', {'page_obj': page_obj, 'query': query})

@login_required
@role_required('ADMIN', 'RECEPTIONIST', 'DOCTOR')
def patient_profile(request, patient_id):
    patient = get_object_or_404(CustomUser, pk=patient_id, role='PATIENT')
    records = MedicalRecord.objects.filter(patient=patient).order_by('-record_date')
    
    # Calculate treatment duration (time since first appointment to now)
    first_appt = Appointment.objects.filter(patient=patient).order_by('date').first()
    duration = "N/A"
    if first_appt:
        diff = timezone.localdate() - first_appt.date
        duration = f"{diff.days} Days"
        
    current_physician = Appointment.objects.filter(patient=patient).order_by('-date').select_related('doctor__user').first()
    
    return render(request, 'hospital/admin/patient_profile.html', {
        'p': patient,
        'records': records,
        'duration': duration,
        'physician': current_physician.doctor.user.display_name if current_physician else "None Assigned"
    })

@login_required
@role_required('ADMIN')
def direct_staff_registration(request):
    if request.method == 'POST':
        form = DirectStaffRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff member registered successfully.')
            return redirect('staff_availability')
    else:
        form = DirectStaffRegistrationForm()
    return render(request, 'hospital/admin/direct_staff_registration.html', {'form': form})

@login_required
def my_profile(request):
    if not request.user.is_staff_role:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = StaffProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('my_profile')
    else:
        form = StaffProfileUpdateForm(instance=request.user)
        
    # Get department for read-only display
    dept = "N/A"
    if request.user.role == 'DOCTOR' and hasattr(request.user, 'doctor_profile'):
        dept = request.user.doctor_profile.department
        
    return render(request, 'hospital/staff/profile.html', {'form': form, 'department': dept})

@login_required
@require_POST
def delete_medical_record(request, record_id):
    record = get_object_or_404(MedicalRecord, pk=record_id)
    # Check permissions: Admin or the one who uploaded it
    if request.user.role == 'ADMIN' or record.uploaded_by == request.user:
        patient_id = record.patient.id
        record.delete()
        messages.success(request, 'Medical record deleted.')
        return redirect('patient_profile', patient_id=patient_id)
    else:
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')
