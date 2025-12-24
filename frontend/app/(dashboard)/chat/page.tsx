'use client';

/**
 * Chat Page - AI-Powered Conversational Interface with OpenAI ChatKit
 *
 * Integrates ChatKit component with custom FastAPI backend using getClientSecret
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSession, fetchJWTToken } from '@/lib/auth-client';
import { ChatKit, useChatKit } from '@openai/chatkit-react';

export default function ChatPage() {
  const { data: session, isPending } = useSession();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Redirect to signin if not authenticated
  useEffect(() => {
    if (!isPending && !session?.user) {
      router.push('/signin');
    }
  }, [session, isPending, router]);

  // ChatKit configuration for custom backend
  const { control } = useChatKit({
    api: {
      // Custom backend URL - ChatKit will POST requests here
      url: `${apiUrl}/chatkit`,
      // Domain key - required for production, skipped on localhost
      domainKey: process.env.NEXT_PUBLIC_CHATKIT_DOMAIN_KEY || 'localhost-dev',
      // Custom fetch to inject our auth headers
      async fetch(input: RequestInfo | URL, init?: RequestInit) {
        console.log('🔵 ChatKit: Custom fetch called', { url: input });

        try {
          // Get JWT token by calling /api/auth/token endpoint
          // This requires an active session (cookies are included automatically)
          const jwtToken = await fetchJWTToken();

          if (!jwtToken) {
            console.error('❌ ChatKit: No JWT token returned from /api/auth/token');
            throw new Error('Not authenticated - please sign in again');
          }

          console.log('✅ ChatKit: JWT token retrieved successfully');

          // Inject auth header with the JWT token
          const headers = {
            ...init?.headers,
            'Authorization': `Bearer ${jwtToken}`,
          };

          console.log('🚀 ChatKit: Fetching with auth header');
          return fetch(input, {
            ...init,
            headers,
          });
        } catch (error) {
          console.error('❌ ChatKit: Error getting token:', error);
          throw new Error('Authentication failed - please sign in again');
        }
      },
    },
    initialThread: null,  // Start with new thread view
    theme: {
      colorScheme: 'light',
      color: {
        accent: {
          primary: '#2563eb', // blue-600
          level: 2,
        },
      },
      radius: 'round',
      density: 'normal',
      typography: { fontFamily: 'system-ui, -apple-system, sans-serif' },
    },
    composer: {
      placeholder: 'Ask me to create tasks, list tasks, or help you manage your todo list...',
    },
    startScreen: {
      greeting: 'Welcome to AI Assistant',
      prompts: [
        {
          label: 'Create a task',
          prompt: 'Create a new task for me',
          icon: 'notebook-pencil',
        },
        {
          label: 'List tasks',
          prompt: 'Show me all my tasks',
          icon: 'search',
        },
        {
          label: 'Get help',
          prompt: 'Help me organize my tasks',
          icon: 'lightbulb',
        },
      ],
    },
    onError: ({ error: err }) => {
      console.error('ChatKit error:', err);
      setError(err?.message || 'An error occurred');
    },
    onThreadChange: ({ threadId }) => {
      console.log('ChatKit: Thread changed', { threadId });
    },
  });

  // Show loading state while checking authentication
  if (isPending) {
    return (
      <div className="flex flex-col h-screen bg-white items-center justify-center">
        <div className="text-center">
          <div className="inline-block">
            <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
          </div>
          <p className="text-gray-600 mt-4">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render ChatKit if not authenticated (will redirect)
  if (!session?.user) {
    return null;
  }

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)]">
      {/* Header Card */}
      <div className="mb-4 bg-white/80 dark:bg-gray-800/80 backdrop-blur-xl rounded-2xl shadow-lg border border-indigo-100 dark:border-indigo-900/50 p-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
            <span className="text-2xl">💬</span>
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
              AI Assistant
            </h1>
            <p className="text-gray-600 dark:text-gray-400 text-xs">
              Chat with your intelligent task manager
            </p>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 rounded-lg shadow-sm">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-red-500 mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
            </svg>
            <div className="flex-1">
              <p className="text-red-800 dark:text-red-300 text-sm font-medium">{error}</p>
              <button
                onClick={() => setError(null)}
                className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200 text-xs mt-2 underline font-semibold"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Chat Container - Ensure it takes remaining height */}
      <div className="flex-1 min-h-0 bg-white/80 dark:bg-gray-800/80 backdrop-blur-xl rounded-2xl shadow-lg border border-indigo-100 dark:border-indigo-900/50 overflow-hidden flex flex-col">
        {/* ChatKit Component - Full height with flex */}
        <div className="flex-1 min-h-0">
          <ChatKit
            control={control}
            className="w-full h-full"
          />
        </div>
      </div>
    </div>
  );
}
