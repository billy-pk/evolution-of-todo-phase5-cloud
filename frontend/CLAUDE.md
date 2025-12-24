# Frontend Guidelines – Next.js App (hackathon-todo)

## Stack
- Next.js 16+ (App Router)
- TypeScript
- Tailwind CSS
- Better Auth for authentication
- API client in `/frontend/lib/api.ts`

## Project Structure
- `/app`         – Routes (App Router) and globals.css
- `/components`  – Reusable UI components (to be created)
- `/lib`         – API client, helpers (to be created)
- `/public`      – Static assets
- `tailwind.config.ts` – Tailwind configuration (root)
- `tsconfig.json` – TypeScript configuration

## API Client Rules
- All backend calls must go through a single client in `lib/api.ts`.
- The client must automatically attach the JWT in the `Authorization: Bearer <token>` header.
- Base URL for API in development: `http://localhost:8000`.

## Auth Rules (Better Auth)
- Implement signup & login pages.
- Use Better Auth’s JWT plugin.
- Expose JWT so `lib/api.ts` can access it.
- JWT must include `user_id` used in backend URLs: `/api/{user_id}/tasks`.

## UI Requirements
- Implement pages and components according to:
  - @specs/ui/pages.md
  - @specs/ui/components.md
- Use Tailwind CSS for styling.
- Pages:
  - `/`          – landing / redirect
  - `/dashboard` – task list and actions
  - `/tasks/new`
  - `/tasks/[id]/edit`

## Current Setup Status
- ✅ Next.js 16 initialized with App Router
- ✅ TypeScript configured
- ✅ Tailwind CSS configured
- ✅ ESLint configured
- ⏳ Better Auth (to be installed in T005)
- ⏳ API client (to be created in T042)
- ⏳ Components (to be created in Phase 4)

## Development Commands
- `npm run dev`    – Start development server (http://localhost:3000)
- `npm run build`  – Build for production
- `npm run lint`   – Run ESLint
- `npm run format` – Format code (when prettier is added)
