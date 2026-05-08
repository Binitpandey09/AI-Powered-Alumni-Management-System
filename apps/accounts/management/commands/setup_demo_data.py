"""
Management command: setup_demo_data

Clears ALL platform data and creates fresh, realistic demo data for
presenting the AlumniAI capstone project.

Usage:
    python manage.py setup_demo_data --settings=alumni_platform.settings.dev
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class Command(BaseCommand):
    help = 'Clear all data and create fresh realistic demo data for presentation'

    # ── Common password for all demo accounts ──────────────────
    PASSWORD = 'Demo@12345'
    COLLEGE  = 'LPU – Lovely Professional University'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('[!]  Clearing all existing platform data…'))
        self._clear_all()
        self.stdout.write(self.style.SUCCESS('[OK]  Data cleared.\n'))

        self.stdout.write('Creating demo users and data…')
        alumni_users  = self._create_alumni()
        faculty_users = self._create_faculty()
        student_users = self._create_students()

        sessions  = self._create_sessions(alumni_users, faculty_users)
        referrals = self._create_referrals(alumni_users, faculty_users)
        self._create_applications(student_users, referrals)
        self._create_feed_posts(alumni_users, faculty_users, referrals, sessions)
        self._create_connections(student_users, alumni_users)

        self.stdout.write('\n' + self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('  Demo data ready!'))
        self.stdout.write(self.style.SUCCESS('  Password for all accounts: ' + self.PASSWORD))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write('')
        self.stdout.write('  Alumni accounts:')
        for u in alumni_users:
            self.stdout.write(f'    {u.email}')
        self.stdout.write('  Faculty accounts:')
        for u in faculty_users:
            self.stdout.write(f'    {u.email}')
        self.stdout.write('  Student accounts:')
        for u in student_users:
            self.stdout.write(f'    {u.email}')

    # ════════════════════════════════════════════════════════════
    # CLEAR ALL DATA
    # ════════════════════════════════════════════════════════════

    def _clear_all(self):
        from apps.notifications.models import Notification, NotificationPreference
        from apps.ratings.models import SessionRating, ReferralRating, UserRatingAggregate
        from apps.payments.models import (
            Transaction, Wallet, PayoutRequest, AIToolUsage, ReferralBoost
        )
        from apps.sessions_app.models import Session, Booking, SessionReview, SessionSlot
        from apps.referrals.models import (
            Referral, ReferralApplication, ReferralSuccessStory,
            FacultyReferralRecommendation
        )
        from apps.feed.models import (
            Post, PostLike, PostComment, PostReport, PostSave,
            ExternalJobApplication
        )
        from apps.accounts.models import (
            Connection, ProfileView,
            AlumniProfile, StudentProfile, FacultyProfile,
            StudentEducation, StudentProject, StudentInternship,
            StudentCertification, StudentAward,
            EmailOTP, User
        )

        # Delete in safe order (children first)
        Notification.objects.all().delete()
        NotificationPreference.objects.all().delete()
        SessionRating.objects.all().delete()
        ReferralRating.objects.all().delete()
        UserRatingAggregate.objects.all().delete()
        Transaction.objects.all().delete()
        PayoutRequest.objects.all().delete()
        AIToolUsage.objects.all().delete()
        ReferralBoost.objects.all().delete()
        Wallet.objects.all().delete()
        Booking.objects.all().delete()
        SessionReview.objects.all().delete()
        try: SessionSlot.objects.all().delete()
        except Exception: pass
        Session.objects.all().delete()
        FacultyReferralRecommendation.objects.all().delete()
        ReferralApplication.objects.all().delete()
        ReferralSuccessStory.objects.all().delete()
        Referral.objects.all().delete()
        ExternalJobApplication.objects.all().delete()
        PostLike.objects.all().delete()
        PostComment.objects.all().delete()
        PostReport.objects.all().delete()
        PostSave.objects.all().delete()
        Post.objects.all().delete()
        Connection.objects.all().delete()
        ProfileView.objects.all().delete()
        EmailOTP.objects.all().delete()
        # Explicitly delete ALL profiles (in case any are attached to superusers)
        AlumniProfile.objects.all().delete()
        StudentProfile.objects.all().delete()
        FacultyProfile.objects.all().delete()
        # Delete all non-superuser users
        User.objects.filter(is_superuser=False).delete()

        self.stdout.write('  Deleted all records.')

    # ════════════════════════════════════════════════════════════
    # CREATE ALUMNI (5)
    # ════════════════════════════════════════════════════════════

    def _create_alumni(self):
        from apps.accounts.models import User, AlumniProfile

        profiles = [
            dict(
                email='priya.sharma@google.com',
                first_name='Priya', last_name='Sharma',
                batch_year=2020,
                profile=dict(
                    company='Google', designation='Software Engineer L3',
                    employment_type='full_time', years_of_experience=4,
                    technical_skills=['Python', 'Django', 'React', 'GCP', 'Kubernetes'],
                    domain_expertise=['Backend Development', 'Cloud Infrastructure'],
                    tools_used=['Git', 'Docker', 'Jira', 'VS Code'],
                    soft_skills=['Leadership', 'Communication', 'Problem Solving'],
                    bio='SWE at Google working on Search infrastructure. LPU CSE alumna (2020). Passionate about helping students land their dream jobs.',
                    advice_for_students='Start DSA early, build real projects, and network genuinely.',
                    linkedin_url='https://linkedin.com/in/priya-sharma',
                    github_url='https://github.com/priya-sharma',
                    available_for_mentorship=True,
                    session_price_range=499,
                    verification_status='verified',
                    impact_score=92, average_rating=Decimal('4.8'),
                    achievements=['Google Spot Bonus 2022', 'Top Performer Q3 2023'],
                    current_location='Bangalore, India',
                )
            ),
            dict(
                email='rahul.verma@microsoft.com',
                first_name='Rahul', last_name='Verma',
                batch_year=2019,
                profile=dict(
                    company='Microsoft', designation='Product Manager',
                    employment_type='full_time', years_of_experience=5,
                    technical_skills=['Product Strategy', 'SQL', 'Python', 'Power BI', 'Azure'],
                    domain_expertise=['Product Management', 'Data Analytics'],
                    tools_used=['Azure DevOps', 'Figma', 'Excel', 'JIRA'],
                    soft_skills=['Strategic Thinking', 'Stakeholder Management', 'Roadmapping'],
                    bio='PM at Microsoft Teams. LPU CSE 2019. Ex-SDE turned PM. Love helping engineers transition into product roles.',
                    advice_for_students='Build products, not just features. Understand the WHY behind everything.',
                    linkedin_url='https://linkedin.com/in/rahul-verma-pm',
                    available_for_mentorship=True,
                    session_price_range=699,
                    verification_status='verified',
                    impact_score=88, average_rating=Decimal('4.7'),
                    achievements=['Best PM Award Microsoft India 2023'],
                    current_location='Hyderabad, India',
                )
            ),
            dict(
                email='anjali.gupta@amazon.com',
                first_name='Anjali', last_name='Gupta',
                batch_year=2021,
                profile=dict(
                    company='Amazon', designation='Data Engineer',
                    employment_type='full_time', years_of_experience=3,
                    technical_skills=['Python', 'Apache Spark', 'AWS', 'Kafka', 'SQL', 'Airflow'],
                    domain_expertise=['Data Engineering', 'Big Data', 'Cloud (AWS)'],
                    tools_used=['AWS Glue', 'Redshift', 'EMR', 'S3', 'Databricks'],
                    soft_skills=['Analytical Thinking', 'Collaboration', 'Documentation'],
                    bio='Data Engineer at Amazon, building pipelines for Prime Video analytics. LPU IT 2021. Open to referrals for data roles at Amazon.',
                    advice_for_students='Master SQL and one big-data framework. The rest follows.',
                    linkedin_url='https://linkedin.com/in/anjali-gupta-data',
                    github_url='https://github.com/anjali-gupta',
                    available_for_mentorship=True,
                    session_price_range=399,
                    verification_status='verified',
                    impact_score=85, average_rating=Decimal('4.9'),
                    achievements=['Amazon Builder Award 2023'],
                    current_location='Bangalore, India',
                )
            ),
            dict(
                email='karan.mehta@tcs.com',
                first_name='Karan', last_name='Mehta',
                batch_year=2022,
                profile=dict(
                    company='TCS', designation='System Engineer',
                    employment_type='full_time', years_of_experience=2,
                    technical_skills=['Java', 'Spring Boot', 'Angular', 'MySQL', 'REST APIs'],
                    domain_expertise=['Full Stack Development', 'Enterprise Applications'],
                    tools_used=['Eclipse', 'Maven', 'Git', 'Postman'],
                    soft_skills=['Teamwork', 'Time Management', 'Quick Learning'],
                    bio='Full Stack Developer at TCS working on banking applications. Happy to help freshers crack TCS interviews.',
                    advice_for_students='Practice coding every day. Consistency beats intensity.',
                    linkedin_url='https://linkedin.com/in/karan-mehta-tcs',
                    available_for_mentorship=True,
                    session_price_range=299,
                    verification_status='verified',
                    impact_score=76, average_rating=Decimal('4.5'),
                    current_location='Pune, India',
                )
            ),
            dict(
                email='sneha.patel@infosys.com',
                first_name='Sneha', last_name='Patel',
                batch_year=2020,
                profile=dict(
                    company='Infosys', designation='DevOps Engineer',
                    employment_type='full_time', years_of_experience=4,
                    technical_skills=['Docker', 'Kubernetes', 'Jenkins', 'Terraform', 'Python', 'Linux'],
                    domain_expertise=['DevOps', 'CI/CD', 'Infrastructure as Code'],
                    tools_used=['AWS', 'Helm', 'Prometheus', 'Grafana', 'GitHub Actions'],
                    soft_skills=['Attention to Detail', 'Crisis Management', 'Documentation'],
                    bio='DevOps Engineer at Infosys. LPU CSE 2020. Passionate about automating everything and helping students enter the DevOps field.',
                    advice_for_students='Linux basics + one cloud platform + Docker = strong DevOps foundation.',
                    linkedin_url='https://linkedin.com/in/sneha-patel-devops',
                    available_for_mentorship=True,
                    session_price_range=349,
                    verification_status='verified',
                    impact_score=81, average_rating=Decimal('4.6'),
                    current_location='Chennai, India',
                )
            ),
        ]

        users = []
        for p in profiles:
            u = User.objects.create_user(
                username=p['email'], email=p['email'],
                password=self.PASSWORD,
                first_name=p['first_name'], last_name=p['last_name'],
                role='alumni', college=self.COLLEGE,
                batch_year=p['batch_year'],
                is_verified=True, is_profile_complete=True, is_active=True,
            )
            # Signal auto-created empty profile; update it with real data
            AlumniProfile.objects.filter(user=u).update(**p['profile'])
            users.append(u)

        self.stdout.write(f'  [OK] Created {len(users)} alumni')
        return users

    # ════════════════════════════════════════════════════════════
    # CREATE FACULTY (5)
    # ════════════════════════════════════════════════════════════

    def _create_faculty(self):
        from apps.accounts.models import User, FacultyProfile

        profiles = [
            dict(
                email='dr.rajesh.kumar@lpu.co.in',
                first_name='Rajesh', last_name='Kumar',
                profile=dict(
                    department='Computer Science & Engineering',
                    designation='Professor',
                    subjects_taught=['Artificial Intelligence', 'Machine Learning', 'Data Structures', 'Algorithms'],
                    years_of_experience=15,
                    bio='Professor of CSE with 15+ years in AI/ML research. PhD from IIT Delhi. Guiding students toward research and top product companies.',
                    average_rating=Decimal('4.8'),
                )
            ),
            dict(
                email='dr.meera.nair@lpu.co.in',
                first_name='Meera', last_name='Nair',
                profile=dict(
                    department='Data Science & Analytics',
                    designation='Associate Professor',
                    subjects_taught=['Data Science', 'Python Programming', 'Statistics', 'Deep Learning'],
                    years_of_experience=10,
                    bio='Associate Professor in Data Science. Ex-data scientist at Wipro. Bridging industry and academia through practical curriculum.',
                    average_rating=Decimal('4.7'),
                )
            ),
            dict(
                email='prof.anil.sharma@lpu.co.in',
                first_name='Anil', last_name='Sharma',
                profile=dict(
                    department='Computer Science & Engineering',
                    designation='Assistant Professor',
                    subjects_taught=['Web Technologies', 'Database Management', 'Cloud Computing', 'Software Engineering'],
                    years_of_experience=7,
                    bio='Assistant Professor specialising in web and cloud technologies. Ex-developer at Accenture. Placement coordinator for CSE batch.',
                    average_rating=Decimal('4.6'),
                )
            ),
            dict(
                email='dr.preethi.iyer@lpu.co.in',
                first_name='Preethi', last_name='Iyer',
                profile=dict(
                    department='Information Technology',
                    designation='Professor',
                    subjects_taught=['Software Engineering', 'Agile Methodologies', 'Project Management', 'Testing'],
                    years_of_experience=18,
                    bio='Professor with 18 years in academia and industry. Certified PMP and Scrum Master. Guiding students in SE best practices.',
                    average_rating=Decimal('4.9'),
                )
            ),
            dict(
                email='prof.vivek.joshi@lpu.co.in',
                first_name='Vivek', last_name='Joshi',
                profile=dict(
                    department='Computer Science & Engineering',
                    designation='Assistant Professor',
                    subjects_taught=['Cloud Computing', 'DevOps', 'Linux', 'Networking'],
                    years_of_experience=5,
                    bio='Assistant Professor and AWS Certified Solutions Architect. Helping students build cloud skills valued by top employers.',
                    average_rating=Decimal('4.5'),
                )
            ),
        ]

        users = []
        for p in profiles:
            u = User.objects.create_user(
                username=p['email'], email=p['email'],
                password=self.PASSWORD,
                first_name=p['first_name'], last_name=p['last_name'],
                role='faculty', college=self.COLLEGE,
                is_verified=True, is_profile_complete=True, is_active=True,
            )
            FacultyProfile.objects.filter(user=u).update(**p['profile'])
            users.append(u)

        self.stdout.write(f'  [OK] Created {len(users)} faculty')
        return users

    # ════════════════════════════════════════════════════════════
    # CREATE STUDENTS (5)
    # ════════════════════════════════════════════════════════════

    def _create_students(self):
        from apps.accounts.models import User, StudentProfile

        profiles = [
            dict(
                email='aryan.singh@lpu.co.in',
                first_name='Aryan', last_name='Singh',
                profile=dict(
                    degree='B.Tech', branch='Computer Science Engineering',
                    graduation_year=2025,
                    skills=['Python', 'Django', 'React', 'SQL', 'Git', 'REST APIs'],
                    profile_summary='Final-year CSE student passionate about full-stack development. Built 3 production projects. Targeting SDE roles at product companies.',
                    looking_for='full_time',
                    github_url='https://github.com/aryan-singh',
                    portfolio_url='https://aryan.dev',
                    current_location='Jalandhar, Punjab',
                    preferred_locations=['Bangalore', 'Hyderabad', 'Pune'],
                    resume_score=82,
                )
            ),
            dict(
                email='riya.desai@lpu.co.in',
                first_name='Riya', last_name='Desai',
                profile=dict(
                    degree='B.Tech', branch='Electronics & Communication Engineering',
                    graduation_year=2025,
                    skills=['Python', 'Machine Learning', 'TensorFlow', 'IoT', 'Embedded C', 'MATLAB'],
                    profile_summary='ECE student with strong ML and embedded systems background. Published research paper on IoT-based health monitoring. Open to data science roles.',
                    looking_for='full_time',
                    github_url='https://github.com/riya-desai',
                    current_location='Jalandhar, Punjab',
                    preferred_locations=['Bangalore', 'Mumbai', 'Chennai'],
                    resume_score=78,
                )
            ),
            dict(
                email='mohit.agarwal@lpu.co.in',
                first_name='Mohit', last_name='Agarwal',
                profile=dict(
                    degree='B.Tech', branch='Computer Science Engineering',
                    graduation_year=2025,
                    skills=['Java', 'Spring Boot', 'MySQL', 'Microservices', 'Docker', 'REST APIs'],
                    profile_summary='Java backend developer with 2 internship experiences. Strong in system design. Targeting backend SDE roles at MNCs.',
                    looking_for='full_time',
                    github_url='https://github.com/mohit-agarwal',
                    current_location='Jalandhar, Punjab',
                    preferred_locations=['Pune', 'Hyderabad', 'Bangalore'],
                    resume_score=85,
                )
            ),
            dict(
                email='kavya.reddy@lpu.co.in',
                first_name='Kavya', last_name='Reddy',
                profile=dict(
                    degree='B.Tech', branch='Information Technology',
                    graduation_year=2025,
                    skills=['Python', 'Machine Learning', 'Data Analysis', 'Pandas', 'NumPy', 'SQL', 'Power BI'],
                    profile_summary='IT student specialising in data science. Kaggle competitions top 15%. Completed AWS Cloud Practitioner certification. Seeking data analyst / data engineer roles.',
                    looking_for='full_time',
                    github_url='https://github.com/kavya-reddy',
                    portfolio_url='https://kaggle.com/kavyareddy',
                    current_location='Jalandhar, Punjab',
                    preferred_locations=['Bangalore', 'Hyderabad', 'Remote'],
                    resume_score=89,
                )
            ),
            dict(
                email='deepak.gupta@lpu.co.in',
                first_name='Deepak', last_name='Gupta',
                profile=dict(
                    degree='B.Tech', branch='Computer Science Engineering',
                    graduation_year=2026,
                    skills=['Python', 'Django', 'Docker', 'Linux', 'Git', 'PostgreSQL'],
                    profile_summary='Pre-final year student actively building backend projects. Currently contributing to open-source. Looking for internship opportunities.',
                    looking_for='internship',
                    github_url='https://github.com/deepak-gupta',
                    current_location='Jalandhar, Punjab',
                    preferred_locations=['Remote', 'Bangalore', 'Delhi'],
                    resume_score=72,
                )
            ),
        ]

        users = []
        for p in profiles:
            u = User.objects.create_user(
                username=p['email'], email=p['email'],
                password=self.PASSWORD,
                first_name=p['first_name'], last_name=p['last_name'],
                role='student', college=self.COLLEGE,
                is_verified=True, is_profile_complete=True, is_active=True,
            )
            StudentProfile.objects.filter(user=u).update(**p['profile'])
            users.append(u)

        self.stdout.write(f'  [OK] Created {len(users)} students')
        return users

    # ════════════════════════════════════════════════════════════
    # CREATE SESSIONS (4)
    # ════════════════════════════════════════════════════════════

    def _create_sessions(self, alumni, faculty):
        from apps.sessions_app.models import Session
        now = timezone.now()

        sessions_data = [
            dict(
                host=alumni[0],  # Priya - Google SWE
                session_type='one_on_one',
                title='Resume Review & Career Planning for SDE Roles',
                description='Get your resume reviewed by a Google SWE. I will give you personalised feedback on your resume, suggest improvements, and help you create a roadmap to land your dream SDE job. We will also cover resume ATS optimisation.',
                skills_covered=['Resume Writing', 'ATS Optimisation', 'Career Planning', 'Goal Setting'],
                scheduled_at=now + timedelta(days=7, hours=2),
                duration_minutes=60, price=Decimal('499'),
                max_seats=1, is_demo_eligible=True,
                meeting_link='https://meet.google.com/priya-resume-session',
                tags=['resume', 'career', 'google', 'sde'],
            ),
            dict(
                host=alumni[1],  # Rahul - Microsoft PM
                session_type='group',
                title='Breaking into Product Management: Roadmap for Engineers',
                description='A group session for engineers who want to transition into Product Management. We will cover PM interviews, case studies, frameworks, and how to build a PM portfolio. Includes real case studies from Microsoft Teams.',
                skills_covered=['Product Management', 'PM Interviews', 'Case Studies', 'Roadmapping'],
                scheduled_at=now + timedelta(days=10, hours=4),
                duration_minutes=90, price=Decimal('699'),
                max_seats=10, is_demo_eligible=True,
                meeting_link='https://teams.microsoft.com/rahul-pm-session',
                tags=['product-management', 'career-switch', 'pm-interview'],
            ),
            dict(
                host=alumni[2],  # Anjali - Amazon Data Engineer
                session_type='group',
                title='Data Engineering Fundamentals: AWS + Spark + SQL',
                description='Hands-on session covering the core skills needed for a data engineering role. Topics: building ETL pipelines with Apache Spark, AWS services for data (S3, Glue, Redshift), and advanced SQL for analytics.',
                skills_covered=['Apache Spark', 'AWS Data Services', 'SQL', 'ETL Pipelines', 'Python'],
                scheduled_at=now + timedelta(days=14, hours=3),
                duration_minutes=120, price=Decimal('399'),
                max_seats=15, is_demo_eligible=False,
                meeting_link='https://zoom.us/anjali-data-session',
                tags=['data-engineering', 'aws', 'spark', 'sql'],
            ),
            dict(
                host=faculty[0],  # Dr. Rajesh - AI/ML Prof
                session_type='group',
                title='Cracking ML Interviews: Concepts, Coding & Case Studies',
                description='Comprehensive session on machine learning interview preparation. Covers ML fundamentals, common interview questions from top companies, Python coding for ML, and real case studies. Based on 200+ mock interviews conducted.',
                skills_covered=['Machine Learning', 'Python', 'Interview Preparation', 'Statistics', 'Neural Networks'],
                scheduled_at=now + timedelta(days=5, hours=5),
                duration_minutes=120, price=Decimal('599'),
                max_seats=20, is_demo_eligible=True,
                meeting_link='https://meet.google.com/dr-rajesh-ml-session',
                tags=['machine-learning', 'interview-prep', 'ai', 'python'],
            ),
        ]

        created = []
        for s in sessions_data:
            obj = Session.objects.create(status='upcoming', **s)
            created.append(obj)

        self.stdout.write(f'  [OK] Created {len(created)} sessions')
        return created

    # ════════════════════════════════════════════════════════════
    # CREATE REFERRALS (5)
    # ════════════════════════════════════════════════════════════

    def _create_referrals(self, alumni, faculty):
        from apps.referrals.models import Referral
        now = timezone.now()

        referrals_data = [
            dict(
                posted_by=alumni[0],  # Priya - Google
                company_name='Google',
                job_title='Software Engineer (University Grad)',
                job_description="""Google is looking for passionate software engineers to join our teams across Search, Maps, YouTube, and Cloud.

Responsibilities:
- Design, develop, test, deploy, maintain, and improve software
- Manage individual project priorities, deadlines and deliverables
- Design and implement solutions to complex engineering challenges

This is a direct referral — I will personally review your application and forward it to the hiring team if you are a strong fit.""",
                work_type='full_time', experience_level='fresher',
                location='Bangalore / Hyderabad', is_remote=False,
                salary_range='₹20–35 LPA + Stock',
                required_skills=['Python', 'Data Structures', 'Algorithms', 'System Design'],
                preferred_skills=['Go', 'Distributed Systems', 'Cloud (GCP/AWS)'],
                max_applicants=3,
                deadline=now + timedelta(days=20),
                is_urgent=True,
                tags=['google', 'sde', 'fresher', 'full-time'],
            ),
            dict(
                posted_by=alumni[2],  # Anjali - Amazon
                company_name='Amazon',
                job_title='Data Engineer – Prime Video Analytics',
                job_description="""Amazon Prime Video is hiring Data Engineers to join the Analytics Platform team.

You will:
- Build and maintain large-scale data pipelines processing petabytes of viewer data
- Work with AWS data services: S3, Glue, Redshift, EMR
- Collaborate with data scientists and product teams

I'm referring candidates from LPU. Strong candidates with Python + SQL + one big-data tool will be prioritised.""",
                work_type='full_time', experience_level='junior',
                location='Bangalore', is_remote=False,
                salary_range='₹18–28 LPA',
                required_skills=['Python', 'SQL', 'Apache Spark', 'AWS'],
                preferred_skills=['Kafka', 'Airflow', 'Databricks'],
                max_applicants=3,
                deadline=now + timedelta(days=25),
                is_urgent=False,
                tags=['amazon', 'data-engineering', 'aws', 'analytics'],
            ),
            dict(
                posted_by=alumni[3],  # Karan - TCS
                company_name='TCS',
                job_title='System Engineer – Java Backend',
                job_description="""TCS is conducting campus-style hiring for LPU students through the alumni referral programme.

Role: System Engineer in the banking & financial services vertical.

Day-to-day:
- Develop and maintain Java Spring Boot microservices
- Work on REST APIs for banking applications
- Collaborate with cross-functional teams

I will walk selected candidates through the TCS hiring process personally.""",
                work_type='full_time', experience_level='fresher',
                location='Pune / Chennai / Hyderabad', is_remote=False,
                salary_range='₹7–10 LPA',
                required_skills=['Java', 'SQL', 'REST APIs'],
                preferred_skills=['Spring Boot', 'Microservices', 'Docker'],
                max_applicants=5,
                deadline=now + timedelta(days=30),
                is_urgent=False,
                tags=['tcs', 'java', 'fresher', 'banking'],
            ),
            dict(
                posted_by=alumni[4],  # Sneha - Infosys
                company_name='Infosys',
                job_title='DevOps Engineer – Infosys BPM',
                job_description="""Infosys is looking for DevOps engineers with cloud and container skills.

Responsibilities:
- Build and manage CI/CD pipelines using Jenkins and GitHub Actions
- Container orchestration with Kubernetes
- Infrastructure provisioning with Terraform on AWS

This referral includes a fast-track interview process for LPU alumni. I will personally prepare shortlisted candidates with a mock interview.""",
                work_type='full_time', experience_level='fresher',
                location='Bangalore / Chennai', is_remote=False,
                salary_range='₹8–12 LPA',
                required_skills=['Docker', 'Linux', 'Python', 'CI/CD'],
                preferred_skills=['Kubernetes', 'Terraform', 'AWS'],
                max_applicants=4,
                deadline=now + timedelta(days=18),
                is_urgent=True,
                tags=['infosys', 'devops', 'cloud', 'fresher'],
            ),
            dict(
                posted_by=faculty[2],  # Prof Anil - placed by faculty
                company_name='Wipro Technologies',
                job_title='Software Developer Trainee',
                job_description="""Wipro is partnering with LPU for direct campus hiring through the faculty referral programme.

Selected candidates will go through:
1. Online coding assessment
2. Technical interview
3. HR round

I will personally recommend eligible students and help them prepare for each stage. Students from CSE, IT, and ECE branches are eligible.""",
                work_type='full_time', experience_level='fresher',
                location='Multiple Locations – PAN India', is_remote=False,
                salary_range='₹6.5–9 LPA',
                required_skills=['Programming Basics', 'SQL', 'Problem Solving'],
                preferred_skills=['Python', 'Java', 'Communication Skills'],
                eligible_branches=['CSE', 'IT', 'ECE'],
                max_applicants=5,
                deadline=now + timedelta(days=35),
                is_urgent=False,
                tags=['wipro', 'fresher', 'campus-hiring', 'multiple-branches'],
            ),
        ]

        created = []
        for r in referrals_data:
            obj = Referral.objects.create(status='active', **r)
            created.append(obj)

        self.stdout.write(f'  [OK] Created {len(created)} referrals')
        return created

    # ════════════════════════════════════════════════════════════
    # CREATE APPLICATIONS (students → referrals)
    # ════════════════════════════════════════════════════════════

    def _create_applications(self, students, referrals):
        from apps.referrals.models import ReferralApplication, Referral

        # (student_idx, referral_idx, score, matched, missing, status, cover)
        apps = [
            (0, 0, 82, ['Python', 'Data Structures', 'Algorithms'],
             ['System Design'], 'shortlisted',
             'I am a final-year CSE student with strong Python and DSA skills. I have built 3 production-level projects and solved 400+ LeetCode problems. Would love to work on Google Search.'),

            (3, 1, 91, ['Python', 'SQL', 'Apache Spark'],
             ['Kafka'], 'shortlisted',
             'I am passionate about data engineering. I have worked with Spark and AWS during my final-year project and have completed the AWS Cloud Practitioner exam.'),

            (2, 2, 88, ['Java', 'SQL', 'REST APIs'],
             [], 'applied',
             'I have 2 internship experiences in Java backend development with Spring Boot. TCS would be my dream company to start my career.'),

            (0, 3, 75, ['Docker', 'Linux', 'Python'],
             ['Kubernetes', 'Terraform'], 'applied',
             'I have hands-on experience with Docker and have completed a Linux fundamentals course. Very keen on building DevOps skills.'),

            (4, 4, 70, ['Python', 'SQL', 'Problem Solving'],
             ['Java'], 'applied',
             'Pre-final year student with strong programming fundamentals. I am available for internship and would love the opportunity to train at Wipro.'),

            (1, 1, 68, ['Python', 'SQL'],
             ['Apache Spark', 'AWS'], 'applied',
             'ECE student with Python and data analysis skills. I am willing to learn Spark and AWS quickly.'),
        ]

        created_count = 0
        for s_idx, r_idx, score, matched, missing, status, cover in apps:
            if s_idx < len(students) and r_idx < len(referrals):
                ref = referrals[r_idx]
                app = ReferralApplication.objects.create(
                    referral=ref,
                    student=students[s_idx],
                    match_score=score,
                    matched_skills=matched,
                    missing_skills=missing,
                    cover_note=cover,
                    status=status,
                )
                # Update referral application count
                Referral.objects.filter(pk=ref.pk).update(
                    total_applications=ReferralApplication.objects.filter(referral=ref).count()
                )
                created_count += 1

        self.stdout.write(f'  [OK] Created {created_count} referral applications')

    # ════════════════════════════════════════════════════════════
    # CREATE FEED POSTS
    # ════════════════════════════════════════════════════════════

    def _create_feed_posts(self, alumni, faculty, referrals, sessions):
        from apps.feed.models import Post
        now = timezone.now()

        posts_data = [
            # Announcements from faculty
            dict(
                author=faculty[0],
                post_type='announcement',
                title='Placement Season 2025 – Final Round of Referrals Open!',
                content='Dear students,\n\nThe placement season is in full swing! We have partnered with 5 top companies this year for direct referrals through our alumni network. Google, Amazon, TCS, Infosys, and Wipro positions are now open on the Referral Board.\n\nCheck your skill match score and apply before deadlines. Faculty team is here to help you with preparation. All the best! [Grad]',
                tags=['placement', 'referrals', 'opportunities'],
                expires_at=now + timedelta(days=30),
            ),
            dict(
                author=faculty[3],
                post_type='announcement',
                title='Mock Interview Drive – Register by This Week',
                content='We are organising a mock interview drive with industry mentors from Google, Microsoft, and Amazon.\n\n[Cal] Date: 2 weeks from now\n⏰ Time: 10 AM – 5 PM\n[Loc] Venue: CSE Seminar Hall\n\nTopics covered: DSA, System Design, HR Round\n\nRegistration is free. Limited to 50 students. Register via the Sessions section.',
                tags=['mock-interview', 'placement', 'preparation'],
                expires_at=now + timedelta(days=14),
            ),
            # Job opportunities from alumni
            dict(
                author=alumni[1],
                post_type='job',
                title='Microsoft Hiring – Associate Product Manager (APM)',
                content='Microsoft is hiring fresh graduates for the Associate PM programme! This is one of the most competitive PM roles for new grads.\n\nWhat you need:\n• Strong analytical thinking\n• Passion for technology products\n• Excellent communication\n\nApply through the link below. I will review applications from LPU students personally.',
                company_name='Microsoft', job_role='Associate Product Manager',
                location='Hyderabad', salary_range='₹25–40 LPA',
                required_skills=['Product Thinking', 'SQL', 'Communication'],
                apply_link='https://careers.microsoft.com/apm',
                tags=['microsoft', 'product-management', 'fresher'],
                expires_at=now + timedelta(days=22),
            ),
            # Session posts
            dict(
                author=alumni[0],
                post_type='session',
                title='[Live] LIVE: Resume Review with Google SWE – Book Your Slot',
                content='I am offering personalised 1-on-1 resume review sessions for students targeting SDE roles.\n\nIn this session we will:\n[OK] Review your resume for ATS compatibility\n[OK] Highlight your strongest projects\n[OK] Tailor it for Google, Microsoft, Amazon JDs\n[OK] Set a 90-day career roadmap\n\nLimited slots available!',
                session_date=now + timedelta(days=7, hours=2),
                session_price=Decimal('499'), session_duration=60,
                max_seats=1,
                session_id=sessions[0].id if sessions else None,
                tags=['resume', 'google', 'career'],
                expires_at=now + timedelta(days=8),
            ),
            dict(
                author=faculty[0],
                post_type='session',
                title='ML Interview Prep – Group Session by Dr. Rajesh Kumar',
                content='Cracking ML interviews requires both theoretical depth and practical coding skills.\n\nThis 2-hour group session covers:\n[Pin] Core ML concepts (guaranteed to be asked)\n[Pin] Python coding for ML tasks\n[Pin] Real case studies from top interviews\n[Pin] Live Q&A\n\nBased on feedback from 200+ students I have guided into data science roles.',
                session_date=now + timedelta(days=5, hours=5),
                session_price=Decimal('599'), session_duration=120,
                max_seats=20,
                session_id=sessions[3].id if len(sessions) > 3 else None,
                tags=['machine-learning', 'interview-prep', 'ai'],
                expires_at=now + timedelta(days=6),
            ),
            # General / achievement posts
            dict(
                author=alumni[2],
                post_type='general',
                title='',
                content='Excited to share that I just completed 3 years at Amazon! [Party]\n\nStarted as a fresher from LPU in 2021, now building data pipelines that serve millions of Prime Video users daily.\n\nTo all LPU students — the journey from campus to a top product company is absolutely achievable. Focus on:\n1. Building real projects\n2. Mastering SQL and one big-data tool\n3. Networking with alumni\n\nFeel free to reach out for a referral or guidance. I am always happy to help! [Rocket]',
                tags=['career', 'amazon', 'motivation', 'alumni'],
                expires_at=now + timedelta(days=90),
            ),
            dict(
                author=alumni[0],
                post_type='general',
                title='',
                content='Just got back from conducting Google\'s campus hiring at IIT Roorkee. Here is what separates candidates who crack Google from those who don\'t:\n\n1. They treat DSA like a daily habit, not last-minute prep\n2. Their projects have real users and real impact\n3. They can explain their code clearly under pressure\n4. They ask great questions at the end of interviews\n\nLPU students — you have the talent. Now build the consistency. Referral slots for the June batch are open. Check the Referral Board! 💙',
                tags=['google', 'placement', 'dsa', 'tips'],
                expires_at=now + timedelta(days=60),
            ),
        ]

        created_count = 0
        for p in posts_data:
            # Referral posts are handled separately via the referral model
            Post.objects.create(status='active', **p)
            created_count += 1

        # Create referral feed posts (linked to actual referral objects)
        for ref in referrals:
            Post.objects.create(
                author=ref.posted_by,
                post_type='referral',
                title=ref.job_title,
                content=ref.job_description[:500],
                company_name=ref.company_name,
                job_role=ref.job_title,
                location=ref.location,
                salary_range=ref.salary_range,
                required_skills=ref.required_skills,
                tags=ref.tags,
                status='active',
                expires_at=ref.deadline,
            )
            # Link this post to the referral
            ref_obj = ref
            post = Post.objects.filter(
                author=ref.posted_by, post_type='referral',
                company_name=ref.company_name, job_role=ref.job_title
            ).last()
            if post:
                ref_obj.feed_posts.set([post])
            created_count += 1

        self.stdout.write(f'  [OK] Created {created_count} feed posts')

    # ════════════════════════════════════════════════════════════
    # CREATE CONNECTIONS
    # ════════════════════════════════════════════════════════════

    def _create_connections(self, students, alumni):
        from apps.accounts.models import Connection, ProfileView

        # Students connected with alumni
        connections = [
            (students[0], alumni[0]),  # Aryan ↔ Priya (Google)
            (students[3], alumni[2]),  # Kavya ↔ Anjali (Amazon Data)
            (students[2], alumni[3]),  # Mohit ↔ Karan (TCS)
            (students[0], alumni[1]),  # Aryan ↔ Rahul (Microsoft PM)
        ]

        for student, alum in connections:
            Connection.objects.create(
                requester=student, receiver=alum,
                status='accepted',
            )

        # Simulate profile views
        for student in students:
            for alum in alumni[:3]:
                ProfileView.objects.create(
                    viewer=student, profile_owner=alum,
                    view_count=2,
                )
        for alum in alumni:
            for student in students[:2]:
                ProfileView.objects.create(
                    viewer=alum, profile_owner=student,
                    view_count=1,
                )

        self.stdout.write(f'  [OK] Created {len(connections)} connections and profile views')
