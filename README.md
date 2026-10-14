# CSAS LMS — College of Statistical & Actuarial Sciences

A local Flask + SQLite learning management system project for the College of Statistical & Actuarial Sciences, Punjab University Lahore.

## Run on Windows
1. Install Python 3.10 or newer.
2. Open PowerShell in the folder containing `app.py`.
3. Run `python -m pip install -r requirements.txt`.
4. Run `python app.py`.
5. Open `http://127.0.0.1:5000` in a browser. Keep PowerShell open while using the app.

## Demo student
- Email: `student@learnspace.edu`
- Password: `Student123!`

## Teacher demo accounts
Each teacher has a separate account and only sees courses assigned to that teacher. These are local project/demo credentials; change them before any real deployment.

| Subject | Teacher login | Demo password |
|---|---|---|
| BSTA-201 — Biostatistics-III (Statistical Inference) | `tahir@csas.pu.edu.pk` | `Tahir@2026` |
| BSTA-202 — Epidemiology | `zulfiqar@csas.pu.edu.pk` | `Zulfiqar@2026` |
| GENG-201 — Expository Writing | `minahil@csas.pu.edu.pk` | `Minahil@2026` |
| GICT-201 — Applications of ICT | `fatima.shahzad@csas.pu.edu.pk` | `FatimaS@2026` |
| SMTH-102 — Linear Algebra | `ghulam.nabi@csas.pu.edu.pk` | `GhulamN@2026` |
| GPST-201 — Pakistan Studies | `fatima.khalid@csas.pu.edu.pk` | `FatimaK@2026` |
| HQ-201 — Understanding of Holy Quran (Fehm-e-Quran) | `shaheen@csas.pu.edu.pk` | `Shaheen@2026` |

The original generic teacher demo account (`teacher@learnspace.edu` / `Teacher123!`) remains available for the original sample courses.

## Features
- Separate student and teacher dashboards
- Teacher-specific subject spaces and logins
- Announcements: teachers can publish to everyone, students, or teachers; readers see notices for their audience
- Attendance: teachers can mark Present / Absent / Late by subject and date; students can view recorded summaries
- Assignment publishing, submissions, grading and feedback
- Learning resources, course pages, timetable and teacher reports
- Responsive teal/navy college theme
- SQLite local database; startup adds the college subjects and teacher accounts without deleting existing local records

## Important notes
- Timetable slots/rooms were not added because the exact times and venues need to be verified against the official timetable image.
- Online meeting links/API credentials, semester GPA/CGPA and official student enrolment data must be supplied/configured before using this as a real college system.
- This is an academic demo, not production-hardened software. Do not expose Flask debug mode to the internet. Set a strong `LMS_SECRET_KEY` and use a production server for deployment.

## Project team
- Ali Raza
- Shaheer Raza Zaidi
- Muhammad Ahmad


## CSAS Punjab University demo accounts (local demo only)

### Student accounts
- Ali Raza — `ali.raza@student.csas.pu.edu.pk` / `AliRaza@2026`
- Shaheer Raza Zaidi — `shaheer.zaidi@student.csas.pu.edu.pk` / `Shaheer@2026`
- Muhammad Ahmad — `muhammad.ahmad@student.csas.pu.edu.pk` / `Ahmad@2026`

### Subject teacher accounts
- Dr. Hafiz Muhammad Tahir — `tahir@csas.pu.edu.pk` / `Tahir@2026`
- Dr. Zulfiqar Ali — `zulfiqar@csas.pu.edu.pk` / `Zulfiqar@2026`
- Ms. Minahil Sada Hussain — `minahil@csas.pu.edu.pk` / `Minahil@2026`
- Ms. Fatima Shahzad — `fatima.shahzad@csas.pu.edu.pk` / `FatimaS@2026`
- Dr. Ghulam Nabi — `ghulam.nabi@csas.pu.edu.pk` / `GhulamN@2026`
- Ms. Fatima Khalid — `fatima.khalid@csas.pu.edu.pk` / `FatimaK@2026`
- Ms. Shaheen Ayyub — `shaheen@csas.pu.edu.pk` / `Shaheen@2026`

These are demonstration credentials for a local class project. Change passwords and secret key before any public deployment. Attendance and coursework charts show database records; official semester GPA/CGPA must be entered/calculated from verified grades. A live generative AI assistant requires an API/provider key; this build does not claim a live AI integration.

## CSAS timetable and notifications update
- The timetable page now uses the supplied official Semester III schedule (effective 07-09-2026), with student-wide and teacher-specific views.
- The Notifications Centre displays recent announcements and deadline reminders generated from saved assignment due dates.
- Grades & Feedback includes a visual score summary and per-assessment progress bars based on saved graded submissions.
- The supplied University of the Punjab building image is used on the landing page.
- Install dependencies with `python -m pip install -r requirements.txt` before running the app.


## Additional student demo accounts
These accounts are created automatically when the app starts:
- Sufiyan — `sufiyan@student.csas.pu.edu.pk` / `Sufiyan@2026`
- Ayesha — `ayesha@student.csas.pu.edu.pk` / `Ayesha@2026`
- Fiza — `fiza@student.csas.pu.edu.pk` / `Fiza@2026`
- Masroor — `masroor@student.csas.pu.edu.pk` / `Masroor@2026`
- Jannat — `jannat@student.csas.pu.edu.pk` / `Jannat@2026`
- Ahsan — `ahsan@student.csas.pu.edu.pk` / `Ahsan@2026`

The homepage hero uses `static/pu-campus.jpg` for the university building image. Timetable remains on its own timetable page.
