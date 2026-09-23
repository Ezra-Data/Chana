"""
Seed data — pre-populates the database on first run with:
- Admin account
- Sample agent account
- Sample student account
- 20 knowledge base entries (realistic campus FAQ content)
- 12 navigation nodes
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.knowledge import KnowledgeEntry
from app.models.navigation import NavNode
from app.middleware.auth import hash_password
from app.services import rag_service

logger = logging.getLogger(__name__)

# ─── Default Accounts ────────────────────────────────────────

DEFAULT_USERS = [
    {
        "email": "admin@campus.edu",
        "name": "System Administrator",
        "hashed_password": hash_password("admin123"),
        "role": UserRole.ADMIN,
    },
    {
        "email": "agent@campus.edu",
        "name": "Sarah Agent",
        "hashed_password": hash_password("agent123"),
        "role": UserRole.AGENT,
    },
    {
        "email": "student@campus.edu",
        "name": "John Kamau",
        "student_reg_no": "CS/2024/001",
        "hashed_password": hash_password("student123"),
        "role": UserRole.STUDENT,
    },
]

# ─── Knowledge Base Entries ──────────────────────────────────

KB_ENTRIES = [
    {
        "category": "academic",
        "title": "Course Registration Process",
        "content": "Course registration is done online through the Student Portal (portal.campus.edu) during the first two weeks of each semester. Steps: 1) Log in with your student credentials. 2) Navigate to 'Course Registration'. 3) Select your courses for the semester. 4) Submit for approval by your academic advisor. 5) Once approved, your timetable will be generated. Late registration (after Week 2) incurs a penalty fee of KSh 5,000. Contact the Registrar's Office in the Admin Block, Room 102, for assistance.",
    },
    {
        "category": "academic",
        "title": "Grading System and GPA Calculation",
        "content": "The university uses the following grading scale: A (70-100%) = 4.0 points, B (60-69%) = 3.0 points, C (50-59%) = 2.0 points, D (40-49%) = 1.0 point, F (below 40%) = 0 points. GPA is calculated by multiplying grade points by credit hours for each course, summing them, and dividing by total credit hours. A minimum cumulative GPA of 2.0 is required to maintain good academic standing. Students with GPA below 2.0 for two consecutive semesters face academic probation.",
    },
    {
        "category": "academic",
        "title": "Exam Rules and Regulations",
        "content": "Examination rules: 1) Arrive at the exam venue at least 15 minutes before the start time. 2) Carry your valid student ID card — no entry without it. 3) No mobile phones, smartwatches, or electronic devices allowed in the exam room. 4) No talking, whispering, or communicating with other candidates. 5) No unauthorized materials (cheat sheets, written notes on body parts). 6) Write your registration number on every answer booklet. Violation of any rule results in automatic disqualification and a disciplinary hearing. Special exam arrangements for students with disabilities should be requested through the Dean of Students' office at least two weeks before exams.",
    },
    {
        "category": "academic",
        "title": "Academic Calendar",
        "content": "The academic year consists of two semesters: Semester 1 runs from September to December, and Semester 2 runs from January to April. The exam period is the last three weeks of each semester. Supplementary/special exams are held in May-June. Inter-semester break is in August. Key dates: Orientation Week (first week of September), Mid-semester break (one week in October/March), Graduation ceremony (July). The detailed academic calendar is published on the university website and student portal at the beginning of each academic year.",
    },
    {
        "category": "academic",
        "title": "Class Timetable and Venue Changes",
        "content": "Class timetables are published on the student portal at the start of each semester. Your personal timetable is generated automatically based on your registered courses. If a class venue or time changes, your department will send a notification via the portal and email. Common lecture venues include: Lecture Hall A-C (Main Academic Block), Computer Labs (ICT Building, 2nd Floor), Science Labs (Science Block). For timetable conflicts, contact your departmental coordinator.",
    },
    {
        "category": "fees",
        "title": "Fee Structure and Payment",
        "content": "Tuition fees vary by program: Undergraduate programs range from KSh 120,000 to KSh 180,000 per semester. Postgraduate programs range from KSh 150,000 to KSh 250,000 per semester. Payment methods accepted: M-Pesa (Paybill 123456, Account = Student Reg No), Bank transfer (University Account, Equity Bank, Account: 0123456789), or at the Finance Office (Admin Block, Ground Floor). Fee payment deadline is the end of Week 3 each semester. Students with outstanding balances above KSh 10,000 cannot sit for exams.",
    },
    {
        "category": "fees",
        "title": "Scholarships and Financial Aid",
        "content": "The university offers several scholarship programs: 1) Merit-based scholarships for students with GPA above 3.5 (covers 25-50% of tuition). 2) Need-based financial aid through the Dean of Students' office. 3) HELB (Higher Education Loans Board) loans — apply online at helb.co.ke. 4) Department-specific scholarships in STEM fields. Application deadline for university scholarships is Week 4 of Semester 1. Required documents: application form, academic transcripts, financial need statement, and recommendation letter from your HOD.",
    },
    {
        "category": "facilities",
        "title": "Library Hours and Services",
        "content": "The University Library is located in the Library Building near the main entrance. Operating hours: Monday to Friday: 8:00 AM to 9:00 PM, Saturday: 9:00 AM to 5:00 PM, Sunday and Public Holidays: Closed. Services available: Book borrowing (max 4 books for 14 days), E-resource access (JSTOR, IEEE, Google Scholar Premium), Quiet study rooms (Book at the front desk), Group discussion rooms (Book online via the portal), Printing and photocopying (Ground floor, KSh 5 per page). Overdue book fine: KSh 20 per day per book.",
    },
    {
        "category": "facilities",
        "title": "Computer Lab Access",
        "content": "Computer labs are located in the ICT Building, 2nd and 3rd floors. Lab 1 and Lab 2 (2nd Floor): General access, 60 computers each. Lab 3 (3rd Floor): Advanced computing, 30 workstations with specialized software. Operating hours: Monday to Friday 7:30 AM to 8:00 PM, Saturday 8:00 AM to 4:00 PM. All students have free access with their student ID. Software available: Microsoft Office, Python, Java, MATLAB, AutoCAD, SPSS. Wi-Fi password for the labs is updated weekly and posted on the lab door.",
    },
    {
        "category": "facilities",
        "title": "Student Health Services",
        "content": "The Campus Health Centre is located next to the Sports Ground. Services: General consultation (free for registered students), First aid and emergency care, Counseling services (mental health support), Referrals to Kenyatta National Hospital for specialized care. Operating hours: Monday to Friday 8:00 AM to 5:00 PM. Emergency line: 0712-345-678 (24/7). All students are covered by the university health insurance (NHIF). Bring your student ID and NHIF card for services.",
    },
    {
        "category": "facilities",
        "title": "Sports and Recreation",
        "content": "Sports facilities include: Football field (behind the Hostel Block), Basketball and volleyball courts (next to the Cafeteria), University gymnasium (Sports Complex, ground floor — open 6 AM to 8 PM), Swimming pool (Sports Complex — open 10 AM to 6 PM, weekdays only). To join a sports team, register with the Sports Office (Sports Complex, Room 5). Inter-university competitions (KUSA games) trials are held in the first month of each semester.",
    },
    {
        "category": "hostel",
        "title": "Hostel Rules and Accommodation",
        "content": "University hostels accommodate 2,000 students. Application is on a first-come, first-served basis through the student portal. Hostel fee: KSh 15,000 per semester. Rules: 1) Curfew: 10:00 PM on weekdays, 11:00 PM on weekends. 2) Visitors must sign in at the gate and leave by 6:00 PM. 3) No cooking in rooms — use the common kitchen. 4) No alcohol or illegal substances on hostel premises. 5) Maintain cleanliness — room inspection every two weeks. 6) Report maintenance issues to the Hostel Warden (Block A, Ground Floor). Violation of rules may result in loss of hostel privileges.",
    },
    {
        "category": "hostel",
        "title": "Off-Campus Housing",
        "content": "Students who prefer off-campus housing can find approved accommodation through the Dean of Students' office. The university maintains a list of approved landlords in the surrounding area. Average rent ranges from KSh 5,000 to KSh 15,000 per month depending on location and amenities. The university shuttle service operates routes to major residential areas: Morning pickups at 6:30 AM, 7:00 AM, 7:30 AM. Evening drop-offs at 5:00 PM, 6:00 PM, 7:00 PM. Shuttle fee: KSh 3,000 per semester.",
    },
    {
        "category": "services",
        "title": "Student ID Card Replacement",
        "content": "If you lose your student ID card: 1) Report the loss to the nearest police station and get a police abstract. 2) Visit the Registrar's Office (Admin Block, Room 102) with: police abstract, one passport-size photo, and KSh 500 replacement fee receipt from the Finance Office. 3) Processing takes 3-5 working days. 4) Collect your new ID from the Registrar's Office. Your student ID is required for: exam entry, library access, lab access, hostel entry, and health centre services. Temporary access passes are available from the Registrar's Office while your replacement is being processed.",
    },
    {
        "category": "services",
        "title": "Transcript and Certificate Requests",
        "content": "To request official transcripts or certificates: 1) Fill out the request form at the Academic Registry (Admin Block, Room 201). 2) Pay the processing fee: Transcript KSh 1,000, Certificate KSh 2,000, Letter of Completion KSh 500. 3) Processing time: 5-10 working days for transcripts, 2-4 weeks for certificates. 4) Collection is from the Academic Registry or by courier (additional KSh 500). For urgent requests, an express fee of KSh 2,000 applies (2-3 working days). Digital transcripts can be requested via email to registry@campus.edu.",
    },
    {
        "category": "services",
        "title": "Campus Wi-Fi Access",
        "content": "Campus-wide Wi-Fi is available in all academic buildings, the library, and common areas. Network name: CampusNet. Login credentials: Your student email and portal password. First-time setup: 1) Connect to 'CampusNet'. 2) Open your browser — you'll be redirected to the login portal. 3) Enter your student email and password. 4) Accept the terms of use. Maximum 3 devices can be connected simultaneously. For connectivity issues, contact the ICT Help Desk: Room 101, ICT Building, or email ict-support@campus.edu. Wi-Fi is available 24/7 but speeds may be reduced during peak hours (10 AM - 2 PM).",
    },
    {
        "category": "procedures",
        "title": "How to File a Complaint",
        "content": "To file a formal complaint or report an issue: Option 1 (Recommended): Use this Smart Campus Companion chatbot — describe your issue and a support ticket will be automatically created with a tracking number. Option 2: Visit the Dean of Students' office (Admin Block, Room 301) during office hours (8 AM - 5 PM). Option 3: Email complaints@campus.edu with your student registration number, detailed description, and any supporting evidence. All complaints are confidential and assigned a tracking number. Expected response time: 24-48 hours for initial acknowledgment, 5-7 working days for resolution. Urgent matters (safety, harassment) are escalated immediately.",
    },
    {
        "category": "procedures",
        "title": "Deferment and Leave of Absence",
        "content": "To defer your studies or take a leave of absence: 1) Obtain a deferment form from the Registrar's Office. 2) Get approval from your Head of Department. 3) Clear any outstanding fees at the Finance Office. 4) Submit all documents to the Registrar's Office. Maximum deferment period: 2 semesters (1 year). You must notify the university at least 2 weeks before the semester starts. Deferment does not exempt you from fee obligations. To resume studies, submit a resumption letter to the Registrar at least 1 month before the semester begins.",
    },
    {
        "category": "procedures",
        "title": "Change of Course or Program",
        "content": "To change your course or program: 1) Obtain a course change form from the Registrar's Office. 2) Get approval from both the current and new department HODs. 3) Meet the entry requirements for the new program. 4) Submit to the Academic Board for approval (meets monthly). Processing time: 2-4 weeks. Course change is only possible within the first two semesters. Credit transfer for completed courses is evaluated case by case. No refund for courses already completed in the previous program.",
    },
    {
        "category": "general",
        "title": "Campus Emergency Contacts",
        "content": "Emergency contacts: Campus Security: 0700-111-222 (24/7). Health Centre Emergency: 0712-345-678 (24/7). Fire Emergency: 0700-333-444. Dean of Students (urgent matters): 0700-555-666. ICT Emergency (system outages): 0700-777-888. Police (Kilimani Station): 0720-999-000 or 999. Ambulance: 0800-723-253. In case of emergency, also alert the nearest security guard or staff member. Emergency assembly points are marked with green signs throughout campus. First aid kits are located in every building's reception area.",
    },
]

# ─── Navigation Nodes ────────────────────────────────────────

NAV_NODES = [
    {
        "name": "Dean's Office",
        "synonyms": ["dean", "dean office", "deans office", "office of the dean", "hod office"],
        "category": "admin",
        "panoee_scene_id": "scene_deans_office",
        "description": "The Dean's Office is located on the 3rd floor of the Admin Block.",
        "building": "Admin Block",
        "floor": "3rd Floor",
    },
    {
        "name": "Main Library",
        "synonyms": ["library", "lib", "reading room", "study area", "book room"],
        "category": "facility",
        "panoee_scene_id": "scene_library",
        "description": "The main university library with study rooms, e-resources, and printing services.",
        "building": "Library Building",
        "floor": "Ground - 2nd Floor",
    },
    {
        "name": "Computer Lab 1",
        "synonyms": ["comp lab", "computer room", "ict lab", "pc lab", "lab 1", "computer lab"],
        "category": "academic",
        "panoee_scene_id": "scene_comp_lab_1",
        "description": "General-access computer lab with 60 workstations.",
        "building": "ICT Building",
        "floor": "2nd Floor",
    },
    {
        "name": "Lecture Hall A",
        "synonyms": ["hall a", "lecture hall", "lh a", "main hall", "lecture theatre a"],
        "category": "academic",
        "panoee_scene_id": "scene_lecture_hall_a",
        "description": "Main lecture hall seating 300 students, equipped with projector and PA system.",
        "building": "Main Academic Block",
        "floor": "Ground Floor",
    },
    {
        "name": "Lecture Hall B",
        "synonyms": ["hall b", "lh b", "lecture theatre b"],
        "category": "academic",
        "panoee_scene_id": "scene_lecture_hall_b",
        "description": "Medium-sized lecture hall seating 150 students.",
        "building": "Main Academic Block",
        "floor": "1st Floor",
    },
    {
        "name": "Lecture Hall C",
        "synonyms": ["hall c", "lh c", "lecture theatre c"],
        "category": "academic",
        "panoee_scene_id": "scene_lecture_hall_c",
        "description": "Small lecture hall seating 80 students, used for tutorials and seminars.",
        "building": "Main Academic Block",
        "floor": "2nd Floor",
    },
    {
        "name": "Admin Block",
        "synonyms": ["administration", "admin", "registrar", "finance office", "fees office", "admin building"],
        "category": "admin",
        "panoee_scene_id": "scene_admin_block",
        "description": "Houses the Registrar's Office, Finance Office, and administrative departments.",
        "building": "Admin Block",
        "floor": "Ground - 3rd Floor",
    },
    {
        "name": "Cafeteria",
        "synonyms": ["cafe", "canteen", "food court", "dining hall", "mess", "eating place", "restaurant"],
        "category": "facility",
        "panoee_scene_id": "scene_cafeteria",
        "description": "Main student cafeteria offering meals from 7 AM to 7 PM.",
        "building": "Student Centre",
        "floor": "Ground Floor",
    },
    {
        "name": "Sports Ground",
        "synonyms": ["sports field", "football field", "pitch", "playground", "field", "stadium"],
        "category": "facility",
        "panoee_scene_id": "scene_sports_ground",
        "description": "Main sports field with football pitch, running track, and spectator stands.",
        "building": "Outdoor",
        "floor": "N/A",
    },
    {
        "name": "Hostel Block A",
        "synonyms": ["hostel", "dorm", "dormitory", "hostels", "residence", "halls of residence"],
        "category": "residential",
        "panoee_scene_id": "scene_hostel_a",
        "description": "Student residential block accommodating 500 students.",
        "building": "Hostel Block A",
        "floor": "Ground - 4th Floor",
    },
    {
        "name": "Exam Hall",
        "synonyms": ["examination hall", "exam room", "exam centre", "examination centre"],
        "category": "academic",
        "panoee_scene_id": "scene_exam_hall",
        "description": "Dedicated examination hall used during exam periods.",
        "building": "Exam Block",
        "floor": "Ground Floor",
    },
    {
        "name": "Health Centre",
        "synonyms": ["clinic", "hospital", "medical centre", "dispensary", "sick bay", "health center"],
        "category": "facility",
        "panoee_scene_id": "scene_health_centre",
        "description": "Campus clinic providing general consultation, first aid, and counseling services.",
        "building": "Health Centre",
        "floor": "Ground Floor",
    },
]


async def seed_database(db: AsyncSession):
    """Seed the database with initial data. Only runs if no admin user exists."""

    # Check if already seeded
    result = await db.execute(select(User).where(User.role == UserRole.ADMIN))
    if result.scalar_one_or_none():
        logger.info("Database already seeded — skipping.")
        return

    logger.info("Seeding database with initial data...")

    # ── Create Users ──────────────────────────────────────────
    for user_data in DEFAULT_USERS:
        user = User(**user_data)
        db.add(user)
    await db.flush()
    logger.info(f"Created {len(DEFAULT_USERS)} users")

    # ── Create Knowledge Base Entries ─────────────────────────
    for entry_data in KB_ENTRIES:
        entry = KnowledgeEntry(**entry_data)
        db.add(entry)
    await db.flush()

    # Embed all KB entries into ChromaDB
    result = await db.execute(select(KnowledgeEntry))
    entries = result.scalars().all()
    for entry in entries:
        rag_service.add_document(
            entry_id=entry.id,
            title=entry.title,
            content=entry.content,
            category=entry.category,
        )
    logger.info(f"Created and embedded {len(KB_ENTRIES)} knowledge base entries")

    # ── Create Navigation Nodes ───────────────────────────────
    for node_data in NAV_NODES:
        node = NavNode(**node_data)
        db.add(node)
    await db.flush()
    logger.info(f"Created {len(NAV_NODES)} navigation nodes")

    await db.commit()
    logger.info("Database seeding complete!")
