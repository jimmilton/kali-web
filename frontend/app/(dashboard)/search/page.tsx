'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  Search,
  Server,
  Bug,
  Key,
  Terminal,
  FolderKanban,
  Loader2,
  Filter,
  X,
} from 'lucide-react';
import Link from 'next/link';

import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PageHeader } from '@/components/layout/breadcrumbs';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface SearchResult {
  id: string;
  type: string;
  title: string;
  subtitle?: string;
  description?: string;
  project_id?: string;
  project_name?: string;
  metadata: Record<string, unknown>;
  score: number;
  highlight?: string;
}

interface SearchResponse {
  query: string;
  total: number;
  results: SearchResult[];
  facets: Record<string, Record<string, number>>;
  page: number;
  page_size: number;
  pages: number;
}

const typeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  asset: Server,
  vulnerability: Bug,
  credential: Key,
  job: Terminal,
  project: FolderKanban,
};

const typeColors: Record<string, string> = {
  asset: 'bg-green-500/10 text-green-500',
  vulnerability: 'bg-red-500/10 text-red-500',
  credential: 'bg-yellow-500/10 text-yellow-500',
  job: 'bg-blue-500/10 text-blue-500',
  project: 'bg-purple-500/10 text-purple-500',
};

export default function SearchPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get('q') || '';

  const [query, setQuery] = useState(initialQuery);
  const [debouncedQuery, setDebouncedQuery] = useState(initialQuery);
  const [entityType, setEntityType] = useState<string>('all');
  const [page, setPage] = useState(1);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  // Update URL
  useEffect(() => {
    if (debouncedQuery) {
      router.replace(`/search?q=${encodeURIComponent(debouncedQuery)}`);
    }
  }, [debouncedQuery, router]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['search', debouncedQuery, entityType, page],
    queryFn: async () => {
      if (!debouncedQuery) return null;
      const params = new URLSearchParams({
        q: debouncedQuery,
        entity_type: entityType,
        page: page.toString(),
        page_size: '20',
      });
      return api.get<SearchResponse>(`/api/v1/search?${params}`);
    },
    enabled: debouncedQuery.length > 0,
  });

  const getResultLink = (result: SearchResult) => {
    switch (result.type) {
      case 'asset':
        return `/projects/${result.project_id}/assets?id=${result.id}`;
      case 'vulnerability':
        return `/projects/${result.project_id}/vulnerabilities?id=${result.id}`;
      case 'credential':
        return `/projects/${result.project_id}/credentials?id=${result.id}`;
      case 'job':
        return `/jobs/${result.id}`;
      case 'project':
        return `/projects/${result.id}`;
      default:
        return '#';
    }
  };

  const clearSearch = () => {
    setQuery('');
    setDebouncedQuery('');
    router.replace('/search');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Search"
        description="Search across all assets, vulnerabilities, credentials, and more"
      />

      {/* Search Input */}
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search for assets, vulnerabilities, credentials..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-10 pr-10"
            autoFocus
          />
          {query && (
            <button
              onClick={clearSearch}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <Select value={entityType} onValueChange={setEntityType}>
          <SelectTrigger className="w-[180px]">
            <Filter className="h-4 w-4 mr-2" />
            <SelectValue placeholder="All types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="assets">Assets</SelectItem>
            <SelectItem value="vulnerabilities">Vulnerabilities</SelectItem>
            <SelectItem value="credentials">Credentials</SelectItem>
            <SelectItem value="jobs">Jobs</SelectItem>
            <SelectItem value="projects">Projects</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Results */}
      {isLoading && debouncedQuery && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {error && (
        <Card className="border-destructive">
          <CardContent className="py-6 text-center text-destructive">
            Failed to search. Please try again.
          </CardContent>
        </Card>
      )}

      {!debouncedQuery && !isLoading && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Search className="h-12 w-12 text-muted-foreground/50" />
            <h3 className="mt-4 text-lg font-semibold">Start searching</h3>
            <p className="mt-2 text-center text-muted-foreground max-w-md">
              Type to search across all your assets, vulnerabilities, credentials, jobs, and
              projects
            </p>
            <div className="mt-4 text-sm text-muted-foreground">
              <kbd className="px-2 py-1 rounded bg-muted">⌘K</kbd> to open command palette
            </div>
          </CardContent>
        </Card>
      )}

      {data && data.results.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Search className="h-12 w-12 text-muted-foreground/50" />
            <h3 className="mt-4 text-lg font-semibold">No results found</h3>
            <p className="mt-2 text-center text-muted-foreground">
              No matches for "{debouncedQuery}". Try a different search term.
            </p>
          </CardContent>
        </Card>
      )}

      {data && data.results.length > 0 && (
        <>
          {/* Result Stats */}
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              Found {data.total} results for "{data.query}"
            </span>
            {data.facets?.entity_type && (
              <div className="flex gap-2">
                {Object.entries(data.facets.entity_type).map(([type, count]) => (
                  <Badge key={type} variant="outline">
                    {type}: {count}
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {/* Result List */}
          <div className="space-y-3">
            {data.results.map((result) => {
              const Icon = typeIcons[result.type] || Search;
              const colorClass = typeColors[result.type] || 'bg-gray-500/10 text-gray-500';

              return (
                <Link key={`${result.type}-${result.id}`} href={getResultLink(result)}>
                  <Card className="hover:bg-accent transition-colors cursor-pointer">
                    <CardContent className="flex items-start gap-4 py-4">
                      <div className={cn('p-2 rounded-lg', colorClass)}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium truncate">{result.title}</h4>
                          <Badge variant="outline" className="text-xs">
                            {result.type}
                          </Badge>
                        </div>
                        {result.subtitle && (
                          <p className="text-sm text-muted-foreground mt-0.5">
                            {result.subtitle}
                          </p>
                        )}
                        {result.description && (
                          <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                            {result.description}
                          </p>
                        )}
                        {result.project_name && (
                          <p className="text-xs text-muted-foreground mt-2">
                            Project: {result.project_name}
                          </p>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              );
            })}
          </div>

          {/* Pagination */}
          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {data.page} of {data.pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= data.pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
