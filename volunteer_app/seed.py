"""
seed.py — populate VolunteerIQ with realistic demo data.
Run once:  python seed.py
Safe to re-run: skips existing emails.
"""

from app import create_app, db
from models import User, Task, Assignment
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

app = create_app()

VOLUNTEERS = [
    {
        'name': 'Priya Sharma',
        'email': 'priya@demo.com',
        'password': 'demo1234',
        'skills': 'first-aid,teaching,hindi,communication',
        'availability': 'Sat All Day,Sun All Day,Mon Evening',
        'bio': 'Passionate about education and community health. 3 years volunteering experience.',
    },
    {
        'name': 'Arjun Mehta',
        'email': 'arjun@demo.com',
        'password': 'demo1234',
        'skills': 'driving,logistics,first-aid,english',
        'availability': 'Fri Evening,Sat All Day,Sun All Day',
        'bio': 'Logistics professional who loves giving back on weekends.',
    },
    {
        'name': 'Sneha Patel',
        'email': 'sneha@demo.com',
        'password': 'demo1234',
        'skills': 'coding,data-entry,social-media,english,teaching',
        'availability': 'Mon Morning,Wed Morning,Fri Morning,Sat All Day',
        'bio': 'Software developer helping NGOs with tech. Available most mornings.',
    },
    {
        'name': 'Rahul Nair',
        'email': 'rahul@demo.com',
        'password': 'demo1234',
        'skills': 'cooking,nutrition,first-aid,hindi',
        'availability': 'Tue Morning,Thu Morning,Sat All Day',
        'bio': 'Chef and nutritionist supporting community meal programmes.',
    },
    {
        'name': 'Aisha Khan',
        'email': 'aisha@demo.com',
        'password': 'demo1234',
        'skills': 'teaching,english,urdu,counselling,communication',
        'availability': 'Mon Morning,Mon Evening,Tue Morning,Wed Morning,Thu Evening',
        'bio': 'School teacher dedicated to adult literacy and youth mentorship.',
    },
    {
        'name': 'Dev Krishnan',
        'email': 'dev@demo.com',
        'password': 'demo1234',
        'skills': 'driving,logistics,carpentry,heavy-lifting',
        'availability': 'Sat All Day,Sun All Day',
        'bio': 'Weekend warrior. Loves hands-on community projects.',
    },
    {
        'name': 'Meera Joshi',
        'email': 'meera@demo.com',
        'password': 'demo1234',
        'skills': 'first-aid,nursing,counselling,hindi,english',
        'availability': 'Mon Morning,Tue Morning,Wed Morning,Thu Morning,Fri Morning',
        'bio': 'Retired nurse with 20 years of medical experience.',
    },
    {
        'name': 'Kabir Singh',
        'email': 'kabir@demo.com',
        'password': 'demo1234',
        'skills': 'social-media,photography,design,coding,english',
        'availability': 'Wed Evening,Thu Evening,Fri Evening,Sat All Day',
        'bio': 'Creative professional supporting NGO communications.',
    },
]

TASKS = [
    {
        'title': 'First Aid at Community Marathon',
        'description': 'Provide basic first aid support at the annual 5K community marathon. Volunteers will be stationed at every 1km mark.',
        'required_skills': 'first-aid,communication',
        'time_slot': 'Saturday 7am – 12pm',
        'location': 'Central Park, Guwahati',
        'priority': 'high',
        'volunteers_needed': 3,
        'status': 'open',
    },
    {
        'title': 'Adult Literacy Workshop',
        'description': 'Conduct a basic reading and writing workshop for adults in the local community centre. Bengali and Hindi speakers preferred.',
        'required_skills': 'teaching,hindi,communication',
        'time_slot': 'Monday 10am – 1pm',
        'location': 'Community Centre, Dispur',
        'priority': 'high',
        'volunteers_needed': 2,
        'status': 'in-progress',
    },
    {
        'title': 'Food Bank Logistics & Delivery',
        'description': 'Help sort, pack and deliver food parcels to 50 families across the city. Drivers must have own vehicle.',
        'required_skills': 'driving,logistics',
        'time_slot': 'Saturday 9am – 3pm',
        'location': 'City Food Bank, Guwahati',
        'priority': 'high',
        'volunteers_needed': 4,
        'status': 'open',
    },
    {
        'title': 'NGO Website Redesign',
        'description': 'Help rebuild and modernise the website for a local environmental NGO. React or plain HTML/CSS experience needed.',
        'required_skills': 'coding,design,english',
        'time_slot': 'Flexible – remote work',
        'location': 'Remote',
        'priority': 'medium',
        'volunteers_needed': 2,
        'status': 'open',
    },
    {
        'title': 'Children\'s Science Camp',
        'description': 'Assist in running a two-day science camp for underprivileged children aged 8–14. Fun experiments and group activities.',
        'required_skills': 'teaching,english,communication',
        'time_slot': 'Sun All Day',
        'location': 'Model School, Jorhat',
        'priority': 'medium',
        'volunteers_needed': 3,
        'status': 'open',
    },
    {
        'title': 'Community Kitchen – Weekend Meals',
        'description': 'Help prepare and serve hot meals to 200+ people at the weekend community kitchen. No cooking experience required for serving.',
        'required_skills': 'cooking,nutrition',
        'time_slot': 'Sunday 8am – 2pm',
        'location': 'Temple Road Kitchen, Guwahati',
        'priority': 'medium',
        'volunteers_needed': 5,
        'status': 'in-progress',
    },
    {
        'title': 'Youth Mental Health Awareness Session',
        'description': 'Facilitate awareness sessions on mental health, stress management, and available support for college students.',
        'required_skills': 'counselling,communication,english',
        'time_slot': 'Thursday Evening 5pm – 8pm',
        'location': 'Cotton University, Guwahati',
        'priority': 'high',
        'volunteers_needed': 2,
        'status': 'open',
    },
    {
        'title': 'Social Media Campaign – Flood Relief',
        'description': 'Create and schedule posts across Instagram, Twitter, and Facebook to raise awareness and donations for flood relief.',
        'required_skills': 'social-media,design,photography',
        'time_slot': 'Flexible – remote',
        'location': 'Remote',
        'priority': 'high',
        'volunteers_needed': 2,
        'status': 'completed',
    },
    {
        'title': 'Elderly Care Home Visit',
        'description': 'Spend time with elderly residents — reading, playing games, or simply talking. Compassion is the only skill needed.',
        'required_skills': 'communication,hindi',
        'time_slot': 'Wednesday Morning 10am – 1pm',
        'location': 'Sunrise Care Home, Guwahati',
        'priority': 'low',
        'volunteers_needed': 4,
        'status': 'open',
    },
    {
        'title': 'Data Entry – Beneficiary Records',
        'description': 'Help digitise 500+ paper beneficiary records for a local NGO\'s new database system.',
        'required_skills': 'data-entry,coding',
        'time_slot': 'Fri Morning 9am – 12pm',
        'location': 'NGO Office, Chandmari',
        'priority': 'low',
        'volunteers_needed': 2,
        'status': 'open',
    },
]

COORDINATOR = {
    'name': 'Anjali Coordinator',
    'email': 'coordinator@demo.com',
    'password': 'demo1234',
    'role': 'coordinator',
}


def seed():
    with app.app_context():
        print('Seeding VolunteerIQ demo data...\n')

        # ── Coordinator ──
        if not User.query.filter_by(email=COORDINATOR['email']).first():
            coord = User(
                name=COORDINATOR['name'],
                email=COORDINATOR['email'],
                password=generate_password_hash(COORDINATOR['password']),
                role='coordinator',
            )
            db.session.add(coord)
            print(f"  ✓ Coordinator: {COORDINATOR['email']}")
        else:
            print(f"  → Coordinator already exists, skipping")

        # ── Volunteers ──
        volunteer_objs = []
        for v in VOLUNTEERS:
            existing = User.query.filter_by(email=v['email']).first()
            if existing:
                print(f"  → Volunteer {v['email']} already exists, skipping")
                volunteer_objs.append(existing)
                continue
            user = User(
                name=v['name'],
                email=v['email'],
                password=generate_password_hash(v['password']),
                role='volunteer',
                skills=v['skills'],
                availability=v['availability'],
                bio=v['bio'],
            )
            db.session.add(user)
            volunteer_objs.append(user)
            print(f"  ✓ Volunteer: {v['name']}")

        db.session.commit()

        # ── Tasks ──
        task_objs = []
        for t in TASKS:
            existing = Task.query.filter_by(title=t['title']).first()
            if existing:
                print(f"  → Task '{t['title'][:40]}' already exists, skipping")
                task_objs.append(existing)
                continue
            task = Task(
                title=t['title'],
                description=t['description'],
                required_skills=t['required_skills'],
                time_slot=t['time_slot'],
                location=t['location'],
                priority=t['priority'],
                volunteers_needed=t['volunteers_needed'],
                status=t['status'],
            )
            db.session.add(task)
            task_objs.append(task)
            print(f"  ✓ Task: {t['title'][:50]}")

        db.session.commit()

        # ── Assignments — create realistic ones ──
        print('\n  Creating assignments...')
        assignment_map = [
            # (volunteer_email, task_title_fragment, status, score)
            ('priya@demo.com',  'Adult Literacy',    'accepted',  85.0),
            ('arjun@demo.com',  'Food Bank',         'accepted',  90.0),
            ('sneha@demo.com',  'NGO Website',       'accepted',  95.0),
            ('rahul@demo.com',  'Community Kitchen', 'accepted',  80.0),
            ('aisha@demo.com',  'Adult Literacy',    'accepted',  88.0),
            ('meera@demo.com',  'First Aid',         'pending',   92.0),
            ('kabir@demo.com',  'Social Media',      'completed', 88.0),
            ('dev@demo.com',    'Food Bank',         'pending',   75.0),
            ('priya@demo.com',  'First Aid',         'accepted',  78.0),
            ('aisha@demo.com',  'Children\'s Science', 'pending', 70.0),
            ('meera@demo.com',  'Youth Mental',      'accepted',  82.0),
            ('sneha@demo.com',  'Data Entry',        'accepted',  91.0),
        ]

        for vol_email, task_fragment, status, score in assignment_map:
            vol  = User.query.filter_by(email=vol_email).first()
            task = Task.query.filter(Task.title.contains(task_fragment)).first()
            if not vol or not task:
                continue
            exists = Assignment.query.filter_by(
                user_id=vol.id, task_id=task.id
            ).first()
            if exists:
                continue
            a = Assignment(
                user_id=vol.id,
                task_id=task.id,
                status=status,
                match_score=score,
            )
            db.session.add(a)
            print(f"  ✓ {vol.name} → {task.title[:35]} [{status}]")

        db.session.commit()
        print('\n✅ Seed complete!\n')
        print('Demo login credentials:')
        print('  Coordinator : coordinator@demo.com / demo1234')
        print('  Volunteer   : priya@demo.com / demo1234')
        print('  Volunteer   : sneha@demo.com / demo1234')
        print('  (all volunteers use password: demo1234)')


if __name__ == '__main__':
    seed()
