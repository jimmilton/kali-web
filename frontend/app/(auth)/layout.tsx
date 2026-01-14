'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Shield } from 'lucide-react';
import { useAuthStore } from '@/stores/auth-store';

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { isAuthenticated, checkAuth } = useAuthStore();

  useEffect(() => {
    const verify = async () => {
      const authenticated = await checkAuth();
      if (authenticated) {
        router.push('/dashboard');
      }
    };
    verify();
  }, [checkAuth, router]);

  return (
    <div className="min-h-screen flex">
      {/* Left side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-primary text-primary-foreground flex-col justify-between p-12">
        <div className="flex items-center gap-2">
          <Shield className="h-8 w-8" />
          <span className="text-2xl font-bold">kwebbie</span>
        </div>
        <div className="space-y-6">
          <h1 className="text-4xl font-bold leading-tight">
            Professional Security Testing
            <br />
            Made Simple
          </h1>
          <p className="text-lg text-primary-foreground/80">
            Run Kali Linux tools through an intuitive web interface.
            Manage projects, track vulnerabilities, and generate reports.
          </p>
          <div className="grid grid-cols-2 gap-4 pt-8">
            <FeatureCard
              title="20+ Tools"
              description="Pre-configured security tools ready to use"
            />
            <FeatureCard
              title="Real-time Output"
              description="Watch tool execution in live terminal"
            />
            <FeatureCard
              title="Result Parsing"
              description="Automatic extraction of findings"
            />
            <FeatureCard
              title="Report Generation"
              description="Professional PDF/DOCX reports"
            />
          </div>
        </div>
        <p className="text-sm text-primary-foreground/60">
          &copy; 2025 milbert.ai. All rights reserved.
        </p>
      </div>

      {/* Right side - Auth form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">{children}</div>
      </div>
    </div>
  );
}

function FeatureCard({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-lg bg-primary-foreground/10 p-4">
      <h3 className="font-semibold">{title}</h3>
      <p className="text-sm text-primary-foreground/70">{description}</p>
    </div>
  );
}
