# Amazon Product Intelligence Platform - Frontend

This is the React frontend for the Amazon Product Intelligence Platform.

## Setup

1. Copy `.env.example` to `.env` and fill in your environment variables:
   ```bash
   cp .env.example .env
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

The application will be available at http://localhost:3000

## Features Implemented

- ✅ Authentication (Login/Register with form validation)
- ✅ Social login integration (Google, GitHub)
- ✅ Protected routes
- ✅ Dashboard with credit balance and usage stats
- ✅ API client with authentication interceptors
- ✅ Error handling and retry logic
- ✅ Responsive layout with mobile support

## Tech Stack

- React 19 with TypeScript
- Vite for build tooling
- TailwindCSS for styling
- React Router for routing
- React Hook Form + Zod for form handling
- TanStack Query for data fetching
- Axios for API calls
- Supabase for social authentication
- Lucide React for icons

## Project Structure

```
src/
├── components/     # Reusable UI components
├── contexts/       # React contexts (Auth)
├── hooks/          # Custom React hooks
├── lib/           # Utilities and API clients
├── pages/         # Page components
└── types/         # TypeScript type definitions
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Environment Variables

- `VITE_API_URL` - Backend API URL (default: http://localhost:8000)
- `VITE_SUPABASE_URL` - Supabase project URL
- `VITE_SUPABASE_ANON_KEY` - Supabase anonymous key