# Frontend Setup - Phase 3 AI Chatbot Todo Application

This is the frontend for the conversational AI todo application built with Next.js, React, TailwindCSS, and Better Auth for authentication.

## Tech Stack
- Next.js 16+ (App Router)
- React 19+
- TypeScript
- TailwindCSS
- Better Auth (JWT authentication)
- OpenAI ChatKit (conversational UI)

## Architecture

**Phase 3 Conversational Interface**:
- All task management operations via natural language chat
- No traditional forms or CRUD UI components
- Pure conversational interface at `/chat`

## Setup Instructions

### 1. Navigate to Frontend Directory
```bash
cd frontend
```

### 2. Install Dependencies
```bash
npm install
# or
yarn install
# or
pnpm install
```

### 3. Environment Configuration
Create a `.env.local` file with:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
BETTER_AUTH_SECRET=<shared-secret>
BETTER_AUTH_URL=http://localhost:3000
DATABASE_URL=postgresql://...
NEXT_PUBLIC_CHATKIT_DOMAIN_KEY=localhost-dev
```

**Important**: `BETTER_AUTH_SECRET` must match the backend configuration.

### 4. Start Development Server
```bash
npm run dev
```

Frontend will be available at: http://localhost:3000

## Project Structure
```
app/
  (auth)/              - Authentication pages (signin, signup)
  (dashboard)/
    chat/             - Main chat interface for task management
  api/auth/           - Better Auth API routes
components/
  Navbar.tsx          - Navigation with chat link
lib/
  api.ts              - API client with JWT authentication
  auth.ts             - Better Auth server configuration
  auth-client.ts      - Better Auth client configuration
  types.ts            - TypeScript type definitions
```

## Key Features
- **Conversational Task Management**: Create, list, update, complete, and delete tasks via natural language
- **Authentication**: Better Auth with JWT tokens
- **Responsive UI**: Mobile-first design with TailwindCSS
- **Real-time Chat**: OpenAI ChatKit integration
- **Persistent Conversations**: Chat history stored in database

## Common Commands
```bash
# Development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run tests
npm test

# Lint code
npm run lint
```

## Integration with Backend

The frontend communicates with:
1. **Backend API** (`NEXT_PUBLIC_API_URL`): Chat endpoint at `/api/{user_id}/chat`
2. **MCP Server** (via backend): Task management tools for AI agent

All authenticated requests automatically include the JWT token in the Authorization header.

## Using the Chat Interface

### Task Operations via Natural Language

**Create tasks**:
- "Add a task to buy groceries"
- "Create a task: finish the report by Friday"

**List tasks**:
- "Show my tasks"
- "List all pending tasks"

**Update tasks**:
- "Update the groceries task to include milk and bread"
- "Change the deadline for the report task"

**Complete tasks**:
- "Mark the groceries task as done"
- "Complete the report task"

**Delete tasks**:
- "Delete the groceries task"
- "Remove the report task"

## Responsive Design

The application is fully responsive and adapts to different viewport sizes:

### Mobile (320px - 768px)
- Hamburger menu in navbar
- Stacked layout for chat interface
- Touch-optimized controls

### Desktop (768px+)
- Full navigation in navbar
- Side-by-side layout
- Keyboard shortcuts enabled

### TailwindCSS Breakpoints
- `sm:` - 640px and up
- `md:` - 768px and up
- `lg:` - 1024px and up
- `xl:` - 1280px and up
- `2xl:` - 1536px and up

## Testing Checklist
- [ ] Sign in successfully
- [ ] Access chat interface at `/chat`
- [ ] Create task via natural language
- [ ] List tasks via natural language
- [ ] Update task via natural language
- [ ] Complete task via natural language
- [ ] Delete task via natural language
- [ ] Test on mobile device
- [ ] Test on desktop browser
- [ ] Verify responsive layout adapts
