import uuid
from django.db import models
from django.conf import settings
from django.db.models import Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Q


# ============================================================
# LECTURE PLAN
# ============================================================

class LecturePlan(models.Model):
    lecture_plan_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    session = models.ForeignKey(
        "LectureSession",   # 🔥 Use string
        on_delete=models.CASCADE,
        related_name="lecture_plans",
        null=True,
        blank=True
    )
    unit_name = models.CharField(max_length=255, null=True, blank=True)
    topic_name = models.CharField(max_length=255, null=True, blank=True)
    subtopic_name = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


# ============================================================
# LECTURE SESSION
# ============================================================

class LectureSession(models.Model):
    allocation = models.ForeignKey(
        'CourseManagement.FacultyAllocation',
        on_delete=models.CASCADE,
        related_name="lecture_sessions"
    )

    session_no = models.IntegerField()
    session_date = models.DateField()
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("allocation", "session_no")
        ordering = ["session_no"]

    def __str__(self):
        return f"Session {self.session_no} - {self.session_date}"


# ============================================================
# ATTENDANCE
# ============================================================
class Attendance(models.Model):
    attendance_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    faculty_allocation = models.ForeignKey(
        "CourseManagement.FacultyAllocation",
        on_delete=models.CASCADE,
        related_name="attendances",
        db_index=True
    )

    lecture_session = models.OneToOneField(
        "faculty.LectureSession",
        on_delete=models.CASCADE,
        related_name="attendance",
        db_index=True
    )

    # ✅ ADD THIS
    date = models.DateField(db_index=True)

    is_submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
    override_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

class StudentAttendance(models.Model):

    STATUS_CHOICES = (
        ("PRESENT", "Present"),
        ("ABSENT", "Absent"),
    )

    attendance = models.ForeignKey(
        Attendance,
        on_delete=models.CASCADE,
        related_name="student_attendances",
        db_index=True
    )

    student = models.ForeignKey(
        "UserDataManagement.Student",
        on_delete=models.CASCADE,
        related_name="attendance_records",
        db_index=True
    )


    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES
    )

    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("attendance", "student")
        ordering = ["student"]

    def __str__(self):
        return f"{self.student} - {self.status}"


# ============================================================
# ASSIGNMENT
# ============================================================

class Assignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    faculty = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assignments"
    )

    academic_class = models.ForeignKey(
        "CourseManagement.AcademicClass",
        on_delete=models.CASCADE
    )

    section = models.ForeignKey(
        "AcademicSetup.Section",
        on_delete=models.CASCADE,
        related_name="students"
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()

    total_marks = models.IntegerField()

    allowed_file_type = models.CharField(
        max_length=100,
        help_text="Example: pdf, docx, jpg"
    )

    attachment = models.FileField(
        upload_to="assignments/",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class StudentSubmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions"
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions"
    )

    file = models.FileField(upload_to="assignment_submissions/")
    submitted_at = models.DateTimeField(auto_now_add=True)

    marks_obtained = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ("assignment", "student")
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.student} - {self.assignment.title}"


# ============================================================
# QUIZ
# ============================================================

class Quiz(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    faculty = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_quizzes"
    )

    academic_class = models.ForeignKey(
        "CourseManagement.AcademicClass",
        on_delete=models.CASCADE
    )

    section = models.ForeignKey(
        "AcademicSetup.Section",
        on_delete=models.CASCADE
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    access_start_datetime = models.DateTimeField()
    access_end_datetime = models.DateTimeField()

    quiz_time = models.IntegerField(
        help_text="Quiz duration in minutes after student starts"
    )

    total_marks = models.IntegerField(default=0)
    is_published = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Question(models.Model):

    QUESTION_TYPES = (
        ("MCQ", "Multiple Choice"),
        ("MSQ", "Multiple Select"),
        ("TRUE_FALSE", "True/False"),
        ("SHORT", "Short Answer"),
        ("LONG", "Long Answer"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    quiz = models.ForeignKey(
        Quiz,
        related_name="questions",
        on_delete=models.CASCADE
    )

    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)

    marks = models.IntegerField()
    order = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quiz.title} - Question"


class Option(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    question = models.ForeignKey(
        Question,
        related_name="options",
        on_delete=models.CASCADE
    )

    option_text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.option_text


class StudentQuizAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="attempts"
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts"
    )

    started_at = models.DateTimeField(auto_now_add=True)
    calculated_end_time = models.DateTimeField()

    submitted_at = models.DateTimeField(null=True, blank=True)
    total_score = models.FloatField(default=0)
    is_submitted = models.BooleanField(default=False)

    class Meta:
        unique_together = ("quiz", "student")

    def __str__(self):
        return f"{self.student.username} - {self.quiz.title}"


class StudentAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    attempt = models.ForeignKey(
        StudentQuizAttempt,
        related_name="answers",
        on_delete=models.CASCADE
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE
    )

    selected_options = models.ManyToManyField(Option, blank=True)
    text_answer = models.TextField(blank=True)

    def __str__(self):
        return f"Answer - {self.question.id}"


# ============================================================
# AUTO UPDATE QUIZ TOTAL MARKS
# ============================================================

def update_quiz_total_marks(quiz):
    total = quiz.questions.aggregate(
        total=Sum("marks")
    )["total"] or 0

    quiz.total_marks = total
    quiz.save(update_fields=["total_marks"])


@receiver(post_save, sender=Question)
def update_total_marks_on_save(sender, instance, **kwargs):
    update_quiz_total_marks(instance.quiz)


@receiver(post_delete, sender=Question)
def update_total_marks_on_delete(sender, instance, **kwargs):
    update_quiz_total_marks(instance.quiz)


# ============================================================
# RESOURCES
# ============================================================

class Resource(models.Model):

    RESOURCE_TYPES = (
        ("PDF", "PDF"),
        ("PPT", "PowerPoint"),
        ("DOC", "Document"),
        ("IMAGE", "Image"),
        ("VIDEO", "Video"),
        ("LINK", "External Link"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    faculty = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_resources"
    )

    academic_class = models.ForeignKey(
        "CourseManagement.AcademicClass",
        on_delete=models.CASCADE
    )

    section = models.ForeignKey(
        "AcademicSetup.Section",
        on_delete=models.CASCADE
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)

    file = models.FileField(upload_to="resources/", null=True, blank=True)
    link = models.URLField(null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
