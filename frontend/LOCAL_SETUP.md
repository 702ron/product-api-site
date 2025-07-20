# Local Development Setup (Without Supabase)

## ✅ Environment Variables Configured

The frontend is now set up for local development with the following configuration:

```env
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://placeholder.supabase.co
VITE_SUPABASE_ANON_KEY=placeholder_key
```

## 🚀 How to Test

1. **Start the backend** (make sure it's running on port 8000):
   ```bash
   # In the main project directory
   uvicorn app.main:app --reload
   ```

2. **Start the frontend** (already running):
   ```bash
   # In the frontend directory
   npm run dev
   ```
   
   Frontend will be available at: http://localhost:3000

## 🔐 Authentication Testing

### ✅ **Email/Password Authentication** (Works)
- Register new account: `/register`
- Login existing account: `/login`
- Uses your backend API for authentication

### ❌ **Social Login** (Disabled in Local Mode)
- Google/GitHub buttons will show error message
- Message: "Social login not available in local development mode"

## 📱 Available Features

- **Login/Register** - Email/password authentication
- **Dashboard** - Shows user info, credit balance, usage stats
- **Protected Routes** - Redirects to login if not authenticated
- **Responsive Design** - Works on mobile and desktop
- **API Integration** - Connected to backend at localhost:8000

## 🧪 Test Flow

1. Go to http://localhost:3000
2. Click "Create a new account"
3. Fill in registration form
4. Should redirect to dashboard
5. See credit balance, user info, and quick actions

## 🔧 Troubleshooting

- **Frontend not loading**: Check if port 3000 is available
- **API errors**: Make sure backend is running on port 8000
- **Social login errors**: Expected behavior in local mode
- **Build errors**: Try `npm install` to refresh dependencies

## 🎯 Next Steps

When ready for production, replace the placeholder Supabase values with real ones from:
1. Create account at supabase.com
2. Create new project
3. Copy URL and anon key from Settings → API
4. Update `.env` file