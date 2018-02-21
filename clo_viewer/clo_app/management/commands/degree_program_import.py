# Import the Degree Programs I saved from the ATA Outcomes file into Django

"""

In this long comment I'm going to go ahead and put down a few notes on the .csv
we're reading from.

The first thing to understand is that this CSV was exported from an excel 
spreadsheet that was meant to be looked at, not fed into a computer program.
That means it's very unclean mixed data, with some rows being purely visual and
others being actual content. 

Each degree program is named in a row, and then its classes follow. The classes
are split into categories which we largely don't care about except electives,
because unlike the other classes electives are not all required to be taken. In
an ideal file format whether a class is an elective would be a checkbox in a 
separate column. But this is not an ideal format so instead it comes in this 
sectioning. That means we either have to manually fix it (eh), or do ugly hack
stuff to make it work (also eh, but my first approach).

Every individual class has a department, label, credits, and then boolean core
learning outcomes. It's necessary to be careful with the credits because the 
person who put together the spreadsheet 'chained together' classes which can be
taken in place of each other. Which by the way, some classes can be taken in 
place of each other so you have to account for that in the data structure too.

[{"label":"My Degree Program Name",
  "credits":90,
  "elective_credits":10,
  "classes":{"id":"MATH 110",
             "label":"Introduction To Linear Algebra",
             "lower_credit_bound":5,
             "upper_credit_bound":10,
             "credit_type":"QS",
             "CLO":{1:False,
                    2:True,
                    3:False,
                      ...}
             "substitutes":[{"id":...}, ...]
             "elective?":False}


"""

import re
import csv
from django.core.management.base import BaseCommand, CommandError
from clo_app import models

class Command(BaseCommand):
    help = "Import JD's manually cleaned .csv of the degree programs and their CLO."

    def add_arguments(self, parser):
        parser.add_argument("filepath", nargs=1, type=str)
        parser.add_argument("--initialize", action="store_true", dest="init")
        parser.add_argument("--delete", action="store_true", dest="delete")
        
    def handle(self, *args, **options):
        if options["init"]:
            self.initialize()
            print("Initial objects were created without errors!")
            return "\n" # Django wraps I/O and tries to concat return value as string
        # Elif because init and delete are mutually exclusive
        elif options["delete"]:
            wumpus_q = input(
            "This will PERMANENTLY DELETE all data currently loaded"
            " in the application, so I just want to be sure you mean it."
            " Type 'wumpus' in to prove you really read this: ")
            if wumpus_q.lower() == "wumpus":
                self.delete_all()
                print("All gone.")
            else:
                print("Nope. Did you include the single quotes? Don't.")
            return "\n"
            
        with open(options["filepath"][0]) as programs_csv:
            degree_programs = csv.reader(programs_csv)
            next(degree_programs)
            ATA_line = next(degree_programs)
            if not ATA_line[0].startswith("ATA"):
                raise Exception("Second line of .csv was not expected ATA line!")
            degree_program_rows = []
            while ATA_line:
                program_rows, new_ATA_line = self.dp_rows(degree_programs, ATA_line)
                program_rows.insert(0, ATA_line)
                degree_program_rows.append(program_rows)
                ATA_line = new_ATA_line
            # On the first pass we construct Degree Programs and Courses
            # This requires an initialization pass to have already been run
            # TODO: Add code checking for the initialization pass and
            # raise error if not present.
            try:
                models.CoreLearningOutcome.objects.get(id=1)
            except models.CoreLearningOutcome.DoesNotExist:
                raise ValueError("You need to run the initialization pass first with"
                                 " --initialize")
                
            dp_objects = []
            course_objects = []
            clo_objects = []
            for dp_rowset in degree_program_rows:
                # Check for "N.A." and correct it to null if found
                try:
                    float(dp_rowset[0][1])
                except ValueError:
                    dp_rowset[0][1] = None
                try:
                    float(dp_rowset[0][2])
                except ValueError:
                    dp_rowset[0][2] = None
                dp = models.DegreeProgram(label=dp_rowset[0][0],
                                          credits=dp_rowset[0][1],
                                          elective_credits=dp_rowset[0][2])
                dp_objects.append(dp)
                course_object_set, clo_set = self.build_courses_from_rows(dp_rowset)
                course_objects += course_object_set
                clo_objects += clo_set

            # Since we reference objects created previously in pass two
            # we have to save the ones made in the first pass.

            [dp.save() for dp in dp_objects]
            [course.save() for course in course_objects]
            print("Degree Programs, Courses and Course Learning Outcomes saved!")

            self.pass_two(degree_program_rows)
            print("Course relationships saved!")
            print("Data imported.")
            
    def pass_two(self, degree_program_rows):
        """On the second pass we construct Degree Program and Course
        Relationships."""
        class_id_re = re.compile("[A-Z]+&* [0-9]+")
        for dp_rowset in enumerate(degree_program_rows):
            degree_program = models.DegreeProgram.objects.get(label=dp_rowset[1][0][0])
            last_parent = (dp_rowset[0], 1)
            # Check to make sure first course in program isn't generic
            # If it is, change it
            if dp_rowset[1][1][0].startswith("Generic"):
                for course_row in enumerate(dp_rowset[1]):
                    if course_row[1][0].startswith("ATA"):
                        continue
                    elif not course_row[1][0].startswith("Generic"):
                        last_parent = (dp_rowset[0], course_row[0])
                        break
                    
            substitute = False
            for row in enumerate(dp_rowset[1]):
                if not class_id_re.fullmatch(row[1][0].strip()):
                    continue
                course_id = row[1][0]
                course_title = row[1][1]
                course_credits = row[1][2]
                
                course = models.Course.objects.get(id=course_id)
                # Set flags on elective, substitute, and generic
                elective = bool(row[1][-1])
                generic = course_id.startswith("Generic")
                # Get parent course
                parent = degree_program_rows[last_parent[0]][last_parent[1]]
                parent_course = models.Course.objects.get(id=parent[0])
                if not substitute and not generic:
                    dpcs = models.DPCourseSpecific(
                        degree_program=degree_program,
                        course=course,
                        elective=elective)
                    dpcs.save()
                    last_parent = (dp_rowset[0], row[0])
                elif generic and not substitute:
                    credit_type = self.extract_generic_credit_type(row[1])
                    dpcg = models.DPCourseGeneric(
                        degree_program=degree_program,
                        credit_type=credit_type,
                        credits=course_credits,
                        elective=elective)
                    dpcg.save()
                    # Omission of last parent update purposeful
                    # as a hack because I don't think this
                    # situation ever actually occurs in the data
                    #TODO: Do this correctly.
                elif substitute and not generic:
                    dp_parent_course = models.DPCourseSpecific.objects.get(
                        degree_program=degree_program,
                        course=parent_course)
                    dpcss = models.DPCourseSubstituteSpecific(
                        parent_course=dp_parent_course,
                        course=course)
                    dpcss.save()
                elif substitute and generic:
                    dp_parent_course = models.DPCourseSpecific.objects.get(
                        degree_program=degree_program,
                        course=parent_course)
                    credit_type = self.extract_generic_credit_type(row[1])
                    dpcsg = models.DPCourseSubstituteGeneric(
                        parent_course=dp_parent_course,
                        credit_type=credit_type,
                        credits=course_credits,
                        elective=elective)
                    dpcsg.save()
                else:
                    raise ValueError("Improper combination of flags!")
                substitute = course_title.strip().endswith("or")

                
        return True

                
                                                           

    def extract_generic_credit_type(self, course_row):
        """Given a course row, extract and return its generic credit type."""
        course_id = row[0]
        credit_type_res = {re.compile("Communication"):"CS",
                           re.compile("Natural Science"):"NS",
                           re.compile("Humanities"):"H",
                           re.compile("Performance"):"HP",
                           re.compile("Social"):"SS",
                           re.compile("Lab"):"NSL",
                           re.compile("Quant"):"QS",
                           re.compile("Elective"):"E",
                           re.compile("Diversity"):"DC",
                           re.compile("Prereq"):"PR"}
        for credit_type_re in credit_type_res:
            if credit_type_re.search(course_id):
                type_string = credit_type_res[credit_type_re]
                credit_type = models.CreditType.objects.get(label_short=type_string)
                return credit_type
            
    def initialize(self):
        """Run an initialization pass if the user requests it. This is necessary
        before we can construct the other objects in the system."""
        # Construct Core Learning Outcomes
        clo_1 = models.CoreLearningOutcome(
                                           label="Engage and take responsibility as active learners",
                                           description=(
                                               "Students will be involved in the" 
                                               " learning process as they gain deeper" 
                                               " levels of understanding of the subject" 
                                               " matter. They will design, complete and"
                                               " analyze projects while developing group" 
                                               " interaction and leadership skills."))
        clo_2 = models.CoreLearningOutcome(
                                           label="Think critically",
                                           description=(
                                               "Students will develop and" 
                                               " practice analytical skills, problem-solving" 
                                               " skills and quantitative reasoning skills." 
                                               " Using creativity and self-reflection," 
                                               " they will be able to engage in inquiry" 
                                               " that produces well-reasoned, meaningful" 
                                               " conclusions."))
        clo_3 = models.CoreLearningOutcome(
                                           label="Communicate effectively",
                                           description=(
                                               "Students will develop the organizational" 
                                               " and research skills necessary to write" 
                                               " and speak effectively. The students will" 
                                               " demonstrate awareness of different" 
                                               " audiences, styles, and approaches to" 
                                               " oral and written communication."))
        clo_4 = models.CoreLearningOutcome(
                                           label="Participate in diverse environments",
                                           description=(
                                               "Students will gain the awareness of" 
                                               " and sensitivity to diversity, including" 
                                               " one’s own place as a global citizen." 
                                               " Students attain knowledge and understanding" 
                                               " of the multiple expressions of diversity," 
                                               " and the skills to recognize, analyze" 
                                               " and evaluate diverse issues and perspectives."))
        clo_5 = models.CoreLearningOutcome(
                                           label="Utilize information literacy skills",
                                           description=(
                                               "Students will develop and employ" 
                                               " skills to recognize when information" 
                                               " is needed and to locate, evaluate," 
                                               " effectively use and communicate" 
                                               " information in its various forms."))
        clo_6 = models.CoreLearningOutcome(
                                           label="Demonstrate computer and technology proficiency",
                                           description=("Students will use computers and" 
                                           " technology as appropriate in their course of study."))
        clo_7 = models.CoreLearningOutcome(
                                           label="Identify elements of a sustainable society",
                                           description=("Students will integrate and" 
                                           " apply economic, ecological, and eco-justice" 
                                           " concepts into a systems-thinking framework."))
        clo_1.save()
        clo_2.save()
        clo_3.save()
        clo_4.save()
        clo_5.save()
        clo_6.save()
        clo_7.save()

        # Construct Credit Types
        CS = models.CreditType(label_short="CS",
                               label="Communication Skills")
        NS = models.CreditType(label_short="NS",
                               label="Natural Science")
        H = models.CreditType(label_short="H",
                              label="Humanities")
        HP = models.CreditType(label_short="HP",
                               label="Humanities Performance")
        SS = models.CreditType(label_short="SS",
                               label="Social Sciences")
        NSL = models.CreditType(label_short="NSL",
                                label="Natural Science Lab")
        QS = models.CreditType(label_short="QS",
                               label="Quantitative Skills")
        E = models.CreditType(label_short="E",
                              label="Elective")
        DC = models.CreditType(label_short="DC",
                               label="Diversity Course")
        PR = models.CreditType(label_short="PR",
                               label="Generic Prerequisite")
        CS.save()
        NS.save()
        H.save()
        HP.save()
        SS.save()
        NSL.save()
        QS.save()
        E.save()
        DC.save()
        PR.save()

    def delete_all(self):
        """Delete every object in the database. This is so you can reseed it.
        Mostly just for debugging."""
        models.CourseLearningOutcome.objects.all().delete()
        #models.CoreLearningOutcome.objects.all().delete()
        #models.CreditType.objects.all().delete()
        models.Course.objects.all().delete()
        models.DegreeProgram.objects.all().delete()
        models.DPCourseSpecific.objects.all().delete()
        models.DPCourseGeneric.objects.all().delete()
        models.DPCourseSubstituteSpecific.objects.all().delete()
        models.DPCourseSubstituteGeneric.objects.all().delete()
        
    def dp_rows(self, csv_reader, ATA_line):
        """Extract the rows corresponding to a particular degree program and return 
        them.

        csv_reader - The CSV reader that returns rows from the data to be imported.
        ATA_line - The degree program line that was previously read."""
        rows = []
        # Compile a regular expression pattern matching class ID's
        class_id_re = re.compile("[A-Z]+&* [0-9]+")
        for row in csv_reader:
            # Exit when we encounter the next ATA row after first
            if row[0].startswith("ATA"):
                return (rows, row)
            elif class_id_re.fullmatch(row[0].strip()):
                rows.append(row)
            elif row[0].startswith("Generic"):
                rows.append(row)
        # This exit point occurs when we run out of rows to read
        return (rows, None)

    def build_courses_from_rows(self, rowset):
        """Take a set of rows from the .csv, and construct course objects from 
        them. Next we construct CourseLearningOutcomes. Then return both."""
        class_id_re = re.compile("[A-Z]+&* [0-9]+")
        courses = []
        course_learning_outcomes = []
        for row in rowset:
            if not class_id_re.fullmatch(row[0].strip()):
                continue
            # If credit is numeric assign it to lower and upper credit bound
            # Otherwise, split the credit range and assign
            try:
                lowercb = float(row[2])
                uppercb = float(row[2])
            except ValueError:
                if "-" in row[2]:
                    bounds = row[2].split("-")
                    lowercb = float(bounds[0])
                    uppercb = float(bounds[1])
                else:
                    lowercb = None
                    uppercb = None
                    
            course = models.Course(id=row[0].strip(),
                                   label=row[1].strip(" or"),
                                   lower_credit_bound=lowercb,
                                   upper_credit_bound=uppercb)
            course.save()

            outcome_string = row[3]
            clo_content = re.findall("[0-9]+", outcome_string)
            for outcome in clo_content:
                core_learning_outcome = models.CoreLearningOutcome.objects.get(
                    id=int(
                        outcome))
                try:
                    models.CourseLearningOutcome.objects.get(
                        course=course,
                        learning_outcome=core_learning_outcome)
                    break
                except models.CourseLearningOutcome.DoesNotExist:
                    course_learning_outcome = models.CourseLearningOutcome(
                        course=course,
                        learning_outcome=core_learning_outcome)
                    course_learning_outcome.save()
                
        return (courses, course_learning_outcomes)
         
            
