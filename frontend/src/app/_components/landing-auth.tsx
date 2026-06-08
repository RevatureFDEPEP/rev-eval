'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { loginSchema, registerSchema, type LoginInput, type RegisterInput, type RegisterOutput } from '@/lib/schemas/auth';

function LoginForm() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
  });

  async function onSubmit(data: LoginInput) {
    setServerError(null);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        setServerError(json.detail || json.error || 'Login failed');
        return;
      }
      router.push('/dashboard');
      router.refresh();
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : 'Network error');
    }
  }

  return (
    <form className="mt-6 space-y-4" onSubmit={handleSubmit(onSubmit)}>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="login-email">Email</label>
        <input
          id="login-email"
          type="email"
          autoComplete="email"
          {...register('email')}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>}
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          autoComplete="current-password"
          {...register('password')}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        {errors.password && <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>}
      </div>
      {serverError && <p className="text-sm text-red-600">{serverError}</p>}
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? 'Working…' : 'Sign in'}
      </Button>
    </form>
  );
}

function RegisterForm() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterInput, unknown, RegisterOutput>({
    resolver: zodResolver(registerSchema),
    defaultValues: { role: 'PARTICIPANT' },
  });

  async function onSubmit(data: RegisterOutput) {
    setServerError(null);
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        setServerError(json.detail || json.error || 'Registration failed');
        return;
      }
      router.push('/dashboard');
      router.refresh();
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : 'Network error');
    }
  }

  return (
    <form className="mt-6 space-y-4" onSubmit={handleSubmit(onSubmit)}>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="reg-fullName">Full name</label>
        <input
          id="reg-fullName"
          type="text"
          {...register('full_name')}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          placeholder="Optional"
        />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="reg-email">Email</label>
        <input
          id="reg-email"
          type="email"
          autoComplete="email"
          {...register('email')}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>}
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="reg-password">Password</label>
        <input
          id="reg-password"
          type="password"
          autoComplete="new-password"
          {...register('password')}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        {errors.password && <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>}
        <p className="mt-1 text-xs text-gray-500">Minimum 8 characters.</p>
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="reg-role">Role</label>
        <select
          id="reg-role"
          {...register('role')}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="PARTICIPANT">Participant</option>
          <option value="TRAINER">Trainer</option>
        </select>
        {errors.role && <p className="mt-1 text-xs text-red-600">{errors.role.message}</p>}
      </div>
      {serverError && <p className="text-sm text-red-600">{serverError}</p>}
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? 'Working…' : 'Register'}
      </Button>
    </form>
  );
}

export function LandingAuth() {
  const [mode, setMode] = useState<'login' | 'register'>('login');

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Welcome</CardTitle>
        <CardDescription>Sign in or create an account to continue.</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs value={mode} onValueChange={(v) => setMode(v as 'login' | 'register')} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="login">Sign in</TabsTrigger>
            <TabsTrigger value="register">Register</TabsTrigger>
          </TabsList>
          <TabsContent value="login" forceMount hidden={mode !== 'login'} />
          <TabsContent value="register" forceMount hidden={mode !== 'register'} />
        </Tabs>
        {mode === 'login' ? <LoginForm /> : <RegisterForm />}
      </CardContent>
    </Card>
  );
}
