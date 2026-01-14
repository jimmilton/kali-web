'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Search,
  Filter,
  Globe,
  ShieldAlert,
  Key,
  Zap,
  Network,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/layout/breadcrumbs';
import { toolsApi, Tool } from '@/lib/api';

const categoryIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  reconnaissance: Network,
  vulnerability_scanning: ShieldAlert,
  web_application: Globe,
  password_attacks: Key,
  exploitation: Zap,
};

const categoryLabels: Record<string, string> = {
  reconnaissance: 'Reconnaissance',
  vulnerability_scanning: 'Vulnerability Scanning',
  web_application: 'Web Application',
  password_attacks: 'Password Attacks',
  exploitation: 'Exploitation',
};

export default function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  useEffect(() => {
    const fetchTools = async () => {
      console.log('API URL:', process.env.NEXT_PUBLIC_API_URL);
      try {
        const data = await toolsApi.list();
        console.log('Tools loaded:', data);
        setTools(data || []);
      } catch (error) {
        console.error('Failed to fetch tools:', error);
        setTools([]);
      } finally {
        setIsLoading(false);
      }
    };
    fetchTools();
  }, []);

  const filteredTools = tools.filter((tool) => {
    const matchesSearch =
      tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tool.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = !categoryFilter || tool.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const groupedTools = filteredTools.reduce(
    (groups, tool) => {
      if (!groups[tool.category]) {
        groups[tool.category] = [];
      }
      groups[tool.category].push(tool);
      return groups;
    },
    {} as Record<string, Tool[]>
  );

  const categories = ['reconnaissance', 'vulnerability_scanning', 'web_application', 'password_attacks', 'exploitation'];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tools"
        description="Browse and run security testing tools"
      />

      {/* Filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search tools..."
            className="pl-10"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button
            variant={categoryFilter === null ? 'default' : 'outline'}
            size="sm"
            onClick={() => setCategoryFilter(null)}
          >
            All
          </Button>
          {categories.map((category) => {
            const Icon = categoryIcons[category];
            return (
              <Button
                key={category}
                variant={categoryFilter === category ? 'default' : 'outline'}
                size="sm"
                onClick={() => setCategoryFilter(category)}
              >
                <Icon className="mr-1 h-4 w-4" />
                {categoryLabels[category]}
              </Button>
            );
          })}
        </div>
      </div>

      {/* Tools Grid */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-48" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : Object.keys(groupedTools).length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Search className="h-12 w-12 text-muted-foreground/50" />
            <h3 className="mt-4 text-lg font-semibold">No tools found</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Try adjusting your search or filters
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-8">
          {categories.map((category) => {
            const categoryTools = groupedTools[category];
            if (!categoryTools || categoryTools.length === 0) return null;

            const Icon = categoryIcons[category];
            return (
              <div key={category}>
                <div className="flex items-center gap-2 mb-4">
                  <Icon className="h-5 w-5 text-primary" />
                  <h2 className="text-lg font-semibold">{categoryLabels[category]}</h2>
                  <Badge variant="secondary">{categoryTools.length}</Badge>
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {categoryTools.map((tool) => (
                    <ToolCard key={tool.slug} tool={tool} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ToolCard({ tool }: { tool: Tool }) {
  const Icon = categoryIcons[tool.category] || Network;

  return (
    <Link href={`/tools/${tool.slug}`}>
      <Card className="card-hover h-full">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Icon className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-lg">{tool.name}</CardTitle>
              </div>
            </div>
          </div>
          <CardDescription className="line-clamp-2">
            {tool.description}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>{tool.parameters.length} parameters</span>
            <Badge variant="outline">{tool.category}</Badge>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
