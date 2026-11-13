# ResumeAI Frontend

## Setup
1. Install Node.js 18+.
2. Run `npm install`.
3. Copy `.env.example` to `.env` and set `VITE_API_URL`.
4. Run `npm run dev`.

The app starts with a Register / Login screen. Create an account with a valid email and a password of at least 8 characters. Each account's resumes and interview records are isolated by the backend.

Live job discovery uses Arbeitnow only. Adzuna has been removed. The built-in demo job catalogue is available from the Job Recommendations page.

PDF preview/export currently uses the browser print dialog. Choose **Save as PDF** in the print destination.
