/**
 * T085: Landing page with welcome message and sign in/sign up links
 *
 * This is the home page of the todo application that welcomes users
 * and provides navigation to authentication pages.
 */

import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-indigo-900">
      {/* Decorative background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-indigo-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-blue-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
      </div>

      {/* Header */}
      <header className="relative container mx-auto px-4 py-6">
        <nav className="flex justify-between items-center backdrop-blur-sm bg-white/30 dark:bg-gray-900/30 rounded-2xl px-6 py-4 shadow-lg border border-white/20">
          <div className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
            ✨ Todo AI
          </div>
          <div className="flex gap-3">
            <Link
              href="/signin"
              className="px-5 py-2.5 text-sm font-medium text-gray-700 hover:text-indigo-600 dark:text-gray-300 dark:hover:text-indigo-400 transition-all duration-200 hover:scale-105"
            >
              Sign In
            </Link>
            <Link
              href="/signup"
              className="px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl hover:from-indigo-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105"
            >
              Sign Up
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="relative container mx-auto px-4 py-16 sm:py-24">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-block mb-6 px-4 py-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-full text-sm font-medium text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
            🚀 AI-Powered Task Management
          </div>

          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold text-gray-900 dark:text-white mb-6 leading-tight">
            Organize Your Tasks with
            <br />
            <span className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent animate-gradient">
              AI Assistance
            </span>
          </h1>

          <p className="text-xl sm:text-2xl text-gray-600 dark:text-gray-300 mb-10 max-w-3xl mx-auto leading-relaxed">
            Chat with your intelligent assistant to manage tasks effortlessly.
            Create, organize, and complete tasks through natural conversation.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
            <Link
              href="/signup"
              className="group w-full sm:w-auto px-10 py-4 text-lg font-semibold text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl hover:from-indigo-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition-all duration-200 shadow-2xl hover:shadow-purple-500/50 hover:scale-105 transform"
            >
              Get Started Free
              <span className="inline-block ml-2 group-hover:translate-x-1 transition-transform">→</span>
            </Link>
            <Link
              href="/signin"
              className="w-full sm:w-auto px-10 py-4 text-lg font-semibold text-indigo-700 bg-white/80 backdrop-blur-sm border-2 border-indigo-200 rounded-2xl hover:bg-white hover:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105 dark:bg-gray-800/80 dark:text-indigo-300 dark:border-indigo-700 dark:hover:bg-gray-800"
            >
              Sign In
            </Link>
          </div>

          {/* Trust badges */}
          <div className="flex flex-wrap justify-center items-center gap-8 text-sm text-gray-500 dark:text-gray-400">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
              </svg>
              <span>100% Free</span>
            </div>
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
              </svg>
              <span>Secure & Private</span>
            </div>
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
              </svg>
              <span>AI-Powered</span>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="mt-32 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <div className="group relative text-center p-8 bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-3xl shadow-xl hover:shadow-2xl transition-all duration-300 border border-white/20 hover:scale-105 hover:-translate-y-2">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 to-purple-500/10 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="relative">
              <div className="inline-flex items-center justify-center w-16 h-16 mb-6 text-4xl bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl shadow-lg">
                <span className="text-white">💬</span>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
                AI Chat Interface
              </h3>
              <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
                Manage tasks through natural conversation. Just tell the AI what you need to do.
              </p>
            </div>
          </div>

          <div className="group relative text-center p-8 bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-3xl shadow-xl hover:shadow-2xl transition-all duration-300 border border-white/20 hover:scale-105 hover:-translate-y-2">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="relative">
              <div className="inline-flex items-center justify-center w-16 h-16 mb-6 text-4xl bg-gradient-to-br from-purple-500 to-pink-600 rounded-2xl shadow-lg">
                <span className="text-white">🔒</span>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
                Secure & Private
              </h3>
              <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
                Your data is encrypted and protected. Only you have access to your tasks.
              </p>
            </div>
          </div>

          <div className="group relative text-center p-8 bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-3xl shadow-xl hover:shadow-2xl transition-all duration-300 border border-white/20 hover:scale-105 hover:-translate-y-2">
            <div className="absolute inset-0 bg-gradient-to-br from-pink-500/10 to-indigo-500/10 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="relative">
              <div className="inline-flex items-center justify-center w-16 h-16 mb-6 text-4xl bg-gradient-to-br from-pink-500 to-indigo-600 rounded-2xl shadow-lg">
                <span className="text-white">⚡</span>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
                Smart & Fast
              </h3>
              <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
                Lightning-fast responses powered by advanced AI. Get things done quicker.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative container mx-auto px-4 py-8 mt-24 border-t border-gray-200/50 dark:border-gray-700/50">
        <div className="text-center text-gray-600 dark:text-gray-400">
          <p className="text-sm">
            &copy; {new Date().getFullYear()} Todo AI. AI-Powered Task Management.
          </p>
        </div>
      </footer>
    </div>
  );
}
