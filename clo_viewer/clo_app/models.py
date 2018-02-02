from django.db import models

class CoreLearningOutcome(models.Model):
    """Represents a CoreLearningOutcome in the class schedule."""
    label = models.TextField()
    description = models.TextField()

class CreditType(models.Model):
    """Represents a credit type such as Quantitative Skills or Natural 
    Science."""
    label_short = models.CharField(primary_key=True, max_length=5)
    label = models.TextField() 
    
class Course(models.Model):
    """Represents a college course."""
    id = models.TextField(primary_key=True)
    label = models.TextField()
    # It turns out that a given course has the possibility of being worth
    # a range of credits.
    # We handle this by defining a lower and upper bound.
    # If a course always gives the same number of credits then these are the
    # same value.
    # By the way, it's also possible to have partial credits which is why
    # they're floats. 
    lower_credit_bound = models.FloatField(null=True)
    upper_credit_bound = models.FloatField(null=True)
    
class CourseLearningOutcome(models.Model):
    """Represents a CoreLearningOutcome associated with a Course."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    learning_outcome = models.ForeignKey(CoreLearningOutcome, on_delete=models.PROTECT)

class DegreeProgram(models.Model):
    """Represents a Degree Program that someone can pursue at EvCC."""
    label = models.TextField()
    credits = models.FloatField()
    elective_credits = models.FloatField(null=True)

    
class DPCourseSpecific(models.Model):
    """Represents a specific Course associated with a Degree Program."""
    degree_program = models.ForeignKey(DegreeProgram, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    elective = models.BooleanField()

class DPCourseGeneric(models.Model):
    """Represents one or more generic course credits associated with a 
    Degree Program."""
    degree_program = models.ForeignKey(DegreeProgram, on_delete=models.CASCADE)
    credit_type = models.ForeignKey(CreditType, on_delete=models.PROTECT)
    credits = models.FloatField(null=True)
    elective = models.BooleanField()

class DPCourseSubstituteSpecific(models.Model):
    """Handle the machine-readable declarations in the class schedule I was 
    given that specify specific substitutions for courses."""
    parent_course = models.ForeignKey(DPCourseSpecific,
                                      on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    
class DPCourseSubstituteGeneric(models.Model):
    """Handle the machine-unreadable declarations in the class schedule I was 
    given that specify generic substitutions for courses."""
    parent_course = models.ForeignKey(DPCourseSpecific,
                                      on_delete=models.CASCADE)
    credit_type = models.ForeignKey(CreditType, on_delete=models.PROTECT)
    credits = models.FloatField(null=True)
    elective = models.BooleanField()
