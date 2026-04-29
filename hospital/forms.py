"""
forms.py — Government Hospital Kashipur
Updated with MedicalRecord logic, file attachments, and EHR support.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import (
    CustomUser, Dependent, Appointment, Medicine, Prescription, 
    Feedback, MedicalRecord, DoctorProfile, PatientVitals, LabOrder
)


# ─────────────────────────────────────────────
#  Doctor Consultation Forms
# ─────────────────────────────────────────────

class VitalsForm(forms.ModelForm):
    class Meta:
        model = PatientVitals
        fields = ('weight', 'bp_systolic', 'bp_diastolic', 'temperature', 'pulse')
        widgets = {
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Weight (kg)'}),
            'bp_systolic': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Systolic'}),
            'bp_diastolic': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Diastolic'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Temp (°F)'}),
            'pulse': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Pulse (bpm)'}),
        }

class LabOrderForm(forms.ModelForm):
    class Meta:
        model = LabOrder
        fields = ('test_name',)
        widgets = {
            'test_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter test name (e.g. CBC, Liver Function Test)'}),
        }


# ─────────────────────────────────────────────
#  Registration Forms
# ─────────────────────────────────────────────

class PatientRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name  = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    email      = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}))
    mobile_no  = forms.CharField(max_length=10, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit Mobile Number'}))
    address    = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full Address'}))

    class Meta:
        model  = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'mobile_no', 'address')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role       = CustomUser.PATIENT
        user.is_approved = True
        if commit:
            user.save()
        return user


class StaffRegistrationForm(UserCreationForm):
    ALLOWED_ROLES = [
        ('DOCTOR',       'Doctor'),
        ('NURSE',        'Nurse'),
        ('PHARMACIST',   'Pharmacist'),
        ('RECEPTIONIST', 'Receptionist'),
    ]
    first_name  = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name   = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email       = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    mobile_no   = forms.CharField(max_length=10, widget=forms.TextInput(attrs={'class': 'form-control'}))
    alt_mobile_no = forms.CharField(max_length=10, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    address     = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    role        = forms.ChoiceField(choices=ALLOWED_ROLES, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model  = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'mobile_no', 'alt_mobile_no', 'address', 'role')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_approved = False
        if commit:
            user.save()
        return user


class DirectStaffRegistrationForm(forms.ModelForm):
    """Admin-only form to register staff without OTP/approval delay."""
    ALLOWED_ROLES = [
        ('DOCTOR',       'Doctor'),
        ('NURSE',        'Nurse'),
        ('PHARMACIST',   'Pharmacist'),
        ('RECEPTIONIST', 'Receptionist'),
    ]
    password         = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    role             = forms.ChoiceField(choices=ALLOWED_ROLES, widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_role'}))
    
    # Conditional fields for Doctor
    department     = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    specialization = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    qualification  = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MBBS, MD'}))

    class Meta:
        model  = CustomUser
        fields = ('first_name', 'last_name', 'username', 'email', 'mobile_no', 'alt_mobile_no', 'address', 'role')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'username':   forms.TextInput(attrs={'class': 'form-control'}),
            'email':      forms.EmailInput(attrs={'class': 'form-control'}),
            'mobile_no':  forms.TextInput(attrs={'class': 'form-control'}),
            'alt_mobile_no': forms.TextInput(attrs={'class': 'form-control'}),
            'address':    forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        
        role = cleaned_data.get('role')
        if role == 'DOCTOR':
            if not cleaned_data.get('department'):
                self.add_error('department', 'Department is required for Doctors.')
            if not cleaned_data.get('specialization'):
                self.add_error('specialization', 'Specialization is required for Doctors.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.is_approved = True
        user.is_active = True
        if commit:
            user.save()
            if user.role == 'DOCTOR':
                DoctorProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        'department': self.cleaned_data.get('department'),
                        'specialization': self.cleaned_data.get('specialization'),
                        'qualification': self.cleaned_data.get('qualification'),
                    }
                )
        return user


class StaffProfileUpdateForm(forms.ModelForm):
    """Staff self-service form for updating password, address, and mobile."""
    new_password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank to keep current'}))
    
    class Meta:
        model = CustomUser
        fields = ('mobile_no', 'alt_mobile_no', 'address')
        widgets = {
            'mobile_no': forms.TextInput(attrs={'class': 'form-control'}),
            'alt_mobile_no': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        p = self.cleaned_data.get('new_password')
        if p:
            user.set_password(p)
        if commit:
            user.save()
        return user


# ─────────────────────────────────────────────
#  Dependent & Appointment Forms
# ─────────────────────────────────────────────

class DependentForm(forms.ModelForm):
    class Meta:
        model   = Dependent
        fields  = ('name', 'dob', 'relation', 'gender')
        widgets = {
            'name':     forms.TextInput(attrs={'class': 'form-control'}),
            'dob':      forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'relation': forms.Select(attrs={'class': 'form-select'}),
            'gender':   forms.Select(attrs={'class': 'form-select'}),
        }


class AppointmentForm(forms.ModelForm):
    class Meta:
        model   = Appointment
        fields  = ('doctor', 'date', 'dependent', 'chief_complaint')
        widgets = {
            'doctor':          forms.Select(attrs={'class': 'form-select'}),
            'date':            forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'dependent':       forms.Select(attrs={'class': 'form-select'}),
            'chief_complaint': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, patient=None, **kwargs):
        super().__init__(*args, **kwargs)
        if patient:
            self.fields['dependent'].queryset = Dependent.objects.filter(patient=patient)
            self.fields['dependent'].required = False
            self.fields['dependent'].empty_label = '— Book for myself —'
        self.fields['doctor'].queryset = DoctorProfile.objects.select_related('user').filter(user__is_active=True, user__is_approved=True)


# ─────────────────────────────────────────────
#  Pharmacy & Inventory Forms
# ─────────────────────────────────────────────

class MedicineForm(forms.ModelForm):
    class Meta:
        model   = Medicine
        fields  = ('medicine_name', 'generic_name', 'batch_number', 'mfg_date', 'expiry_date', 'total_quantity', 'unit', 'shelf_location', 'is_active')
        widgets = {
            'medicine_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'generic_name':   forms.TextInput(attrs={'class': 'form-control'}),
            'batch_number':   forms.TextInput(attrs={'class': 'form-control'}),
            'mfg_date':       forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date':    forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'total_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit':           forms.Select(attrs={'class': 'form-select'}),
            'shelf_location': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active':      forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class StockUpdateForm(forms.Form):
    ACTION_CHOICES = [('ADD', '➕ Add Stock'), ('REMOVE', '➖ Remove Stock')]
    action           = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    quantity_changed = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    reason           = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))


class PrescriptionForm(forms.ModelForm):
    class Meta:
        model   = Prescription
        fields  = ('medicine', 'dosage', 'quantity_prescribed', 'duration_days', 'instructions', 'next_visit_date')
        widgets = {
            'medicine':           forms.Select(attrs={'class': 'form-select', 'id': 'medicine-select'}),
            'dosage':             forms.TextInput(attrs={'class': 'form-control'}),
            'quantity_prescribed':forms.NumberInput(attrs={'class': 'form-control'}),
            'duration_days':      forms.NumberInput(attrs={'class': 'form-control'}),
            'instructions':       forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'next_visit_date':    forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }


# ─────────────────────────────────────────────
#  Feedback & EHR Forms
# ─────────────────────────────────────────────

class FeedbackForm(forms.ModelForm):
    class Meta:
        model   = Feedback
        fields  = ('subject', 'message', 'urgency', 'file_attachment')
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'urgency': forms.Select(attrs={'class': 'form-select'}),
            'file_attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }


class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model   = MedicalRecord
        fields  = ('linked_member', 'title', 'file', 'category', 'record_date', 'description')
        widgets = {
            'linked_member': forms.Select(attrs={'class': 'form-select'}),
            'title':       forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Blood Report Feb 2024'}),
            'file':        forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'category':    forms.Select(attrs={'class': 'form-select'}),
            'record_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, patient=None, **kwargs):
        super().__init__(*args, **kwargs)
        if patient:
            from .models import Dependent
            self.fields['linked_member'].queryset = Dependent.objects.filter(patient=patient)
            self.fields['linked_member'].empty_label = f"{patient.display_name} (Self)"
            self.fields['linked_member'].label = "Report For"
            self.fields['linked_member'].required = False

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if f and f.size > 5 * 1024 * 1024:
            raise forms.ValidationError('File must not exceed 5 MB.')
        return f
