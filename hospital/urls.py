"""
urls.py — Government Hospital Kashipur
Full routes including EHR, Pharmacy Availability, and standard appointments.
"""

from django.urls import path
from . import views

urlpatterns = [
    # ── Auth ──────────────────────────────────────
    path('',                        views.login_view,           name='login'),
    path('login/',                  views.login_view,           name='login'),
    path('logout/',                 views.logout_view,          name='logout'),
    path('register/',               views.register_patient,     name='register_patient'),
    path('register/staff/',         views.register_staff,       name='register_staff'),

    # ── Dashboard ─────────────────────────────────
    path('dashboard/',              views.dashboard,            name='dashboard'),

    # ── Medical Records & EHR ─────────────────────
    path('ehr/',                                    views.ehr_dashboard,        name='ehr_dashboard'),
    path('ehr/upload/',                             views.upload_past_history,  name='upload_past_history'),
    path('ehr/appointment/<int:appointment_id>/upload/', views.upload_report,    name='upload_report'),

    # ── Pharmacy & Availability ───────────────────
    path('pharmacy/availability/',                  views.medicine_availability, name='medicine_availability'),
    path('pharmacy/inventory/',                     views.inventory_list,       name='inventory_list'),
    path('pharmacy/inventory/add/',                 views.add_medicine,         name='add_medicine'),
    path('pharmacy/inventory/<int:medicine_id>/stock/', views.update_stock,     name='update_stock'),
    path('pharmacy/autocomplete/',                  views.medicine_autocomplete, name='medicine_autocomplete'),
    path('pharmacy/audit-log/',                     views.audit_log_view,       name='audit_log'),

    # ── Appointments ──────────────────────────────
    path('appointments/book/',              views.book_appointment,     name='book_appointment'),
    path('appointments/<int:appointment_id>/queue/', views.live_queue, name='live_queue'),
    path('appointments/<int:appointment_id>/',        views.appointment_detail, name='appointment_detail'),
    path('appointments/<int:appointment_id>/prescribe/', views.prescribe,       name='prescribe'),

    # ── Doctor & Clinical Workflow ────────────────
    path('doctor/queue/',           views.doctor_queue,         name='doctor_queue'),
    path('doctor/call-next/',       views.call_next,            name='call_next'),
    path('doctor/consultation/<int:appointment_id>/', views.active_consultation, name='active_consultation'),
    path('doctor/lab-order/<int:appointment_id>/',    views.create_lab_order,    name='create_lab_order'),
    path('doctor/ehr-search/',      views.ehr_search,           name='ehr_search'),
    path('doctor/availability/toggle/', views.toggle_availability, name='toggle_availability'),

    # ── Dependents ────────────────────────────────
    path('dependents/add/',                 views.add_dependent,    name='add_dependent'),
    path('dependents/<int:dep_id>/delete/', views.delete_dependent, name='delete_dependent'),

    # ── Feedback ──────────────────────────────────
    path('feedback/submit/',                views.submit_feedback,      name='submit_feedback'),
    path('feedback/inbox/',                 views.feedback_inbox,       name='feedback_inbox'),
    path('feedback/dashboard/',             views.feedback_dashboard,   name='feedback_dashboard'),
    path('feedback/<int:feedback_id>/resolve/', views.resolve_feedback, name='resolve_feedback'),

    # ── Admin Actions ─────────────────────────────
    path('admin-panel/approve/<int:user_id>/', views.approve_staff, name='approve_staff'),
    path('admin-panel/staff/availability/', views.staff_availability, name='staff_availability'),
    path('admin-panel/staff/register/', views.direct_staff_registration, name='direct_staff_registration'),
    path('admin-panel/patients/', views.all_patient_records, name='all_patient_records'),
    path('admin-panel/patients/<int:patient_id>/', views.patient_profile, name='patient_profile'),
    path('admin-panel/records/<int:record_id>/delete/', views.delete_medical_record, name='delete_medical_record'),

    # ── Staff Profile ─────────────────────────────
    path('profile/', views.my_profile, name='my_profile'),
]
