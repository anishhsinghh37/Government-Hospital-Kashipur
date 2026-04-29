"""
models.py — Government Hospital Kashipur
All core data models supporting EHR, Pharmacy availability, and Feedback updates.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


# ─────────────────────────────────────────────
#  Validators
# ─────────────────────────────────────────────

def validate_file_size(value):
    """Reject medical report uploads larger than 5 MB."""
    limit = 5 * 1024 * 1024
    if value.size > limit:
        raise ValidationError('File size must not exceed 5 MB. Please compress the file and try again.')


def validate_150_words(value):
    """Constraint: Feedback message must not exceed 150 words."""
    if len(value.split()) > 150:
        raise ValidationError('Message exceeds 150 words. Please shorten your feedback.')


phone_validator = RegexValidator(
    regex=r'^[6-9]\d{9}$',
    message='Enter a valid 10-digit Indian mobile number starting with 6-9.'
)


# ─────────────────────────────────────────────
#  1. Custom User
# ─────────────────────────────────────────────

class CustomUser(AbstractUser):
    PATIENT      = 'PATIENT'
    DOCTOR       = 'DOCTOR'
    NURSE        = 'NURSE'
    PHARMACIST   = 'PHARMACIST'
    RECEPTIONIST = 'RECEPTIONIST'
    ADMIN        = 'ADMIN'

    ROLE_CHOICES = [
        (PATIENT,      'Patient'),
        (DOCTOR,       'Doctor'),
        (NURSE,        'Nurse'),
        (PHARMACIST,   'Pharmacist'),
        (RECEPTIONIST, 'Receptionist'),
        (ADMIN,        'Admin'),
    ]

    role         = models.CharField(max_length=20, choices=ROLE_CHOICES, default=PATIENT)
    mobile_no    = models.CharField(max_length=10, validators=[phone_validator], db_index=True, blank=True, null=True)
    alt_mobile_no= models.CharField(max_length=10, validators=[phone_validator], blank=True, null=True)
    address      = models.TextField(blank=True, null=True)
    is_approved  = models.BooleanField(
        default=False,
        help_text='Staff must be approved by Admin before they can log in.'
    )
    is_available = models.BooleanField(default=False)


    class Meta:
        verbose_name      = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    @property
    def is_staff_role(self):
        return self.role in [self.DOCTOR, self.NURSE, self.PHARMACIST, self.RECEPTIONIST, self.ADMIN]

    @property
    def display_name(self):
        return self.get_full_name() or self.username


# ─────────────────────────────────────────────
#  2. Dependent (family members managed by a patient)
# ─────────────────────────────────────────────

class Dependent(models.Model):
    RELATION_CHOICES = [
        ('SELF',   'Self'),
        ('SPOUSE', 'Spouse'),
        ('SON',    'Son'),
        ('DAUGHTER', 'Daughter'),
        ('FATHER', 'Father'),
        ('MOTHER', 'Mother'),
        ('SIBLING', 'Sibling'),
        ('OTHER',  'Other'),
    ]
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    patient  = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name='dependents',
        limit_choices_to={'role': CustomUser.PATIENT}
    )
    name     = models.CharField(max_length=150, db_index=True)
    dob      = models.DateField(verbose_name='Date of Birth')
    relation = models.CharField(max_length=20, choices=RELATION_CHOICES)
    gender   = models.CharField(max_length=1, choices=GENDER_CHOICES)

    class Meta:
        verbose_name      = 'Dependent'
        verbose_name_plural = 'Dependents'
        unique_together   = ('patient', 'name', 'dob')

    def __str__(self):
        return f"{self.name} ({self.get_relation_display()}) of {self.patient.display_name}"


# ─────────────────────────────────────────────
#  3. Doctor Profile
# ─────────────────────────────────────────────

class DoctorProfile(models.Model):
    user           = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE,
        related_name='doctor_profile',
        limit_choices_to={'role': CustomUser.DOCTOR}
    )
    specialization = models.CharField(max_length=200)
    department     = models.CharField(max_length=200, db_index=True)
    qualification  = models.CharField(max_length=200, blank=True, null=True, help_text="e.g. MBBS, MD, MS")
    available_days = models.CharField(
        max_length=50, default='MON,TUE,WED,THU,FRI',
        help_text='Comma-separated: MON,TUE,...'
    )
    consultation_start = models.TimeField(default='09:00')
    consultation_end   = models.TimeField(default='17:00')
    max_patients_per_day = models.PositiveIntegerField(default=30)

    class Meta:
        verbose_name      = 'Doctor Profile'
        verbose_name_plural = 'Doctor Profiles'

    def __str__(self):
        return f"Dr. {self.user.display_name} — {self.specialization}"


# ─────────────────────────────────────────────
#  4. Appointment 
# ─────────────────────────────────────────────

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('WAITING',    'Waiting'),
        ('IN_PROGRESS','In Progress'),
        ('COMPLETED',  'Completed'),
        ('CANCELLED',  'Cancelled'),
    ]

    patient      = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name='appointments',
        limit_choices_to={'role': CustomUser.PATIENT}
    )
    dependent    = models.ForeignKey(
        Dependent, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='appointments'
    )
    doctor       = models.ForeignKey(
        DoctorProfile, on_delete=models.CASCADE,
        related_name='appointments'
    )
    date         = models.DateField(db_index=True)
    booking_time = models.DateTimeField(auto_now_add=True, db_index=True)
    token_number = models.PositiveIntegerField(editable=False, default=0)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='WAITING', db_index=True)
    chief_complaint = models.TextField(blank=True)
    notes        = models.TextField(blank=True)
    doctor_advice = models.TextField(blank=True, help_text="Final advice for the patient.")
    next_visit_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name      = 'Appointment'
        verbose_name_plural = 'Appointments'
        ordering          = ['date', 'token_number']
        indexes           = [
            models.Index(fields=['date', 'doctor', 'status']),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            today_count = Appointment.objects.filter(
                doctor=self.doctor,
                date=self.date
            ).count()
            self.token_number = today_count + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Token #{self.token_number} — {self.patient_display_name} ({self.date})"

    @property
    def patient_display_name(self):
        return self.dependent.name if self.dependent else self.patient.display_name

    @property
    def wait_time_minutes(self):
        """Calculate wait time from booking to now if waiting."""
        if self.status == 'WAITING':
            diff = timezone.now() - self.booking_time
            return int(diff.total_seconds() / 60)
        return 0


# ─────────────────────────────────────────────
#  5. Patient Vitals
# ─────────────────────────────────────────────

class PatientVitals(models.Model):
    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE,
        related_name='vitals'
    )
    weight      = models.DecimalField(max_digits=5, decimal_places=2, help_text="kg")
    bp_systolic = models.PositiveIntegerField(help_text="mmHg")
    bp_diastolic= models.PositiveIntegerField(help_text="mmHg")
    temperature = models.DecimalField(max_digits=4, decimal_places=1, help_text="°F")
    pulse       = models.PositiveIntegerField(help_text="bpm", null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Vitals for {self.appointment}"

    @property
    def blood_pressure(self):
        return f"{self.bp_systolic}/{self.bp_diastolic}"


# ─────────────────────────────────────────────
#  6. Lab Order
# ─────────────────────────────────────────────

class LabOrder(models.Model):
    ORDER_STATUS = [
        ('PENDING',   'Pending'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE,
        related_name='lab_orders'
    )
    test_name   = models.CharField(max_length=255)
    ordered_by  = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    status      = models.CharField(max_length=20, choices=ORDER_STATUS, default='PENDING')
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.test_name} for {self.appointment.patient_display_name}"


# ─────────────────────────────────────────────
#  7. Medicine / Inventory
# ─────────────────────────────────────────────

class Medicine(models.Model):
    UNIT_CHOICES = [
        ('TAB',  'Tablet'), ('CAP',  'Capsule'), ('SYR',  'Syrup'), ('INJ',  'Injection'),
        ('DROP', 'Drops'), ('OIN',  'Ointment'), ('POW',  'Powder'), ('OTHER','Other'),
    ]

    medicine_name  = models.CharField(max_length=200, db_index=True)
    generic_name   = models.CharField(max_length=200, blank=True, db_index=True)
    batch_number   = models.CharField(max_length=100, db_index=True)
    mfg_date       = models.DateField()
    expiry_date    = models.DateField(db_index=True)
    total_quantity = models.PositiveIntegerField(default=0)
    unit           = models.CharField(max_length=10, choices=UNIT_CHOICES, default='TAB')
    shelf_location = models.CharField(max_length=100, blank=True)
    is_active      = models.BooleanField(default=True, db_index=True)
    added_by       = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True
    )
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name      = 'Medicine'
        verbose_name_plural = 'Medicines'
        ordering          = ['medicine_name']

    def __str__(self):
        return f"{self.medicine_name} ({self.total_quantity})"

    @property
    def is_in_stock(self):
        return self.total_quantity > 0

    @property
    def is_expired(self):
        return self.expiry_date < timezone.localdate()


# ─────────────────────────────────────────────
#  6. Prescription
# ─────────────────────────────────────────────

class Prescription(models.Model):
    STOCK_STATUS = [
        ('FREE_IN_STOCK',  '✅ FREE — In Stock'),
        ('OUT_OF_STOCK',   '❌ Out of Stock — Purchase Outside'),
        ('EXPIRED',        '⚠️ Expired'),
    ]

    appointment    = models.ForeignKey(
        Appointment, on_delete=models.CASCADE,
        related_name='prescriptions'
    )
    medicine       = models.ForeignKey(
        Medicine, on_delete=models.PROTECT,
        related_name='prescriptions'
    )
    dosage         = models.CharField(max_length=200)
    duration_days  = models.PositiveIntegerField(default=5)
    quantity_prescribed = models.PositiveIntegerField(default=1)
    instructions   = models.TextField(blank=True)
    stock_status   = models.CharField(max_length=20, choices=STOCK_STATUS, editable=False)
    prescribed_by  = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True
    )
    prescribed_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.medicine} for {self.appointment}"


# ─────────────────────────────────────────────
#  7. Feedback
# ─────────────────────────────────────────────

class Feedback(models.Model):
    URGENCY_CHOICES = [
        ('RED',    '🔴 RED — Emergency'),
        ('YELLOW', '🟡 YELLOW — Warning'),
        ('GREEN',  '🟢 GREEN — Advice / Suggestion'),
    ]

    sender     = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    subject    = models.CharField(max_length=300)
    message    = models.TextField(validators=[validate_150_words])
    urgency    = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='GREEN')
    file_attachment = models.FileField(
        upload_to='feedback/',
        null=True, blank=True,
        validators=[validate_file_size],
        help_text='Max 5MB'
    )
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('RESOLVED', 'Resolved'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN', db_index=True)
    is_resolved = models.BooleanField(default=False)
    admin_response = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name_plural = 'Feedbacks'
        ordering          = ['-created_at']


# ─────────────────────────────────────────────
#  8. Stock Audit Log
# ─────────────────────────────────────────────

class StockAuditLog(models.Model):
    ACTION_CHOICES = [
        ('ADD',    'Added to Stock'),
        ('REMOVE', 'Removed from Stock'),
        ('DISPENSE','Dispensed via Prescription'),
    ]

    pharmacist       = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    medicine         = models.ForeignKey(Medicine, on_delete=models.SET_NULL, null=True)
    action           = models.CharField(max_length=20, choices=ACTION_CHOICES)
    quantity_changed = models.IntegerField()
    quantity_before  = models.PositiveIntegerField()
    quantity_after   = models.PositiveIntegerField()
    reason           = models.TextField()
    timestamp        = models.DateTimeField(auto_now_add=True, db_index=True)
    prescription     = models.ForeignKey(
        Prescription, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ['-timestamp']


# ─────────────────────────────────────────────
#  9. Medical Record (EHR)
# ─────────────────────────────────────────────

class MedicalRecord(models.Model):
    CATEGORY_CHOICES = [
        ('LAB_REPORT',   'Lab Report'),
        ('PAST_HISTORY', 'Archived Past History'),
    ]

    patient     = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name='medical_records',
        limit_choices_to={'role': CustomUser.PATIENT}
    )
    appointment = models.ForeignKey(
        Appointment, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='records'
    )
    linked_member = models.ForeignKey(
        Dependent, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='medical_records',
        help_text='Leave blank if the record is for the account holder (Self).'
    )
    title       = models.CharField(max_length=200)
    file        = models.FileField(
        upload_to='ehr/',
        validators=[validate_file_size],
        help_text='Max 5MB'
    )
    category    = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='LAB_REPORT')
    record_date = models.DateField(db_index=True)
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Medical Records'
        ordering          = ['-record_date', '-uploaded_at']
