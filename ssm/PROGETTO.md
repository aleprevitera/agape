\# SSM Simulator WebApp Specification



\## 1. Project Overview

Build a React web application tailored for Italian medical residents preparing for the SSM (Concorso Nazionale Specializzazioni Mediche). 

\- \*\*Target Audience:\*\* Small group of medical students.

\- \*\*Hosting:\*\* GitHub Pages (must be a static SPA).

\- \*\*Design Philosophy:\*\* "Medical Minimalist". Clean typography (Inter/Roboto), plenty of whitespace, subtle shadows, no "AI slop" (avoid excessive gradients or futuristic neon elements). Look like a serious study tool (e.g., Amboss, UpToDate).



\## 2. Tech Stack

\- \*\*Framework:\*\* React (Vite).

\- \*\*Styling:\*\* Tailwind CSS + Shadcn/UI.

\- \*\*State Management:\*\* Zustand.

\- \*\*Backend/DB:\*\* Supabase (Free Tier).

&nbsp;   - Use Supabase Auth for user login (Email/Password or Magic Link).

&nbsp;   - Use Supabase Database (Postgres) to store user progress.

\- \*\*Hosting:\*\* GitHub Pages.



\## 3. Core Features



\### A. Data Handling

\- \*\*Questions:\*\* Still load read-only questions from `/public/questions.jsonl` (no need to put these in DB to keep it simple, unless we want to track stats per question ID).

\- \*\*User Data (Supabase):\*\*

    - `profiles` table: link to auth.users, stores nickname.

    - `exam\\\_results` table: stores the result of each simulation (user\_id, timestamp, score, wrong\_answers\_ids, subject\_breakdown\_json).



\### B. Simulation Modes

1\.  \*\*SSM Simulation (Classic):\*\* - 140 Questions.

&nbsp;   - Timer (210 minutes).

&nbsp;   - Logic to distribute questions based on "Materia" (Distribution logic to be defined, strictly random for now).

2\.  \*\*Custom Simulation:\*\* - User selects subjects ("Materia").

&nbsp;   - User selects number of questions.

3\.  \*\*Speed Run:\*\* - 20 random questions from all subjects.

&nbsp;   - Focus on speed.



\### C. The "Smart Profile" (Sync Logic)

\- On app launch, fetch `exam\\\_results` from Supabase for the logged-in user.

\- Calculate weak subjects dynamically from this history.

\- \*\*Sync:\*\* When a user finishes a quiz, push the result object to Supabase immediately.



\### D. The Interface (UI/UX)

\- \*\*Dashboard:\*\* Welcome screen with user stats (doughnut charts for performance), "Continue Studying" button, and mode selection cards.

\- \*\*Quiz Interface:\*\* - Clean layout: Question text on left/top, options on right/bottom.

&nbsp;   - Distraction-free mode.

&nbsp;   - "Flag for review" button.

&nbsp;   - Immediate feedback mode vs. Exam mode (feedback at the end).

&nbsp;   - Image zoom modal for `image\_src`.

\- \*\*Review Screen:\*\* Detailed breakdown of the completed exam. Show "Commento" only here.



\## 4. Constraints

\- Must be deployable to GitHub Pages (use `base` path in Vite config).

\- No external database.

\- Responsive (Mobile friendly is critical).

