'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, Plus, X, Globe, Network } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { PageHeader } from '@/components/layout/breadcrumbs';
import { useToast } from '@/components/ui/use-toast';
import { useProjectStore } from '@/stores/project-store';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

const projectSchema = z.object({
  name: z.string().min(1, 'Project name is required').max(100),
  description: z.string().max(500).optional(),
});

type ProjectForm = z.infer<typeof projectSchema>;

export default function NewProjectPage() {
  const router = useRouter();
  const { createProject, isLoading } = useProjectStore();
  const { toast } = useToast();

  const [domains, setDomains] = useState<string[]>([]);
  const [ips, setIps] = useState<string[]>([]);
  const [excludes, setExcludes] = useState<string[]>([]);
  const [domainInput, setDomainInput] = useState('');
  const [ipInput, setIpInput] = useState('');
  const [excludeInput, setExcludeInput] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProjectForm>({
    resolver: zodResolver(projectSchema),
  });

  const addDomain = () => {
    if (domainInput && !domains.includes(domainInput)) {
      setDomains([...domains, domainInput]);
      setDomainInput('');
    }
  };

  const addIp = () => {
    if (ipInput && !ips.includes(ipInput)) {
      setIps([...ips, ipInput]);
      setIpInput('');
    }
  };

  const addExclude = () => {
    if (excludeInput && !excludes.includes(excludeInput)) {
      setExcludes([...excludes, excludeInput]);
      setExcludeInput('');
    }
  };

  const removeDomain = (domain: string) => {
    setDomains(domains.filter((d) => d !== domain));
  };

  const removeIp = (ip: string) => {
    setIps(ips.filter((i) => i !== ip));
  };

  const removeExclude = (exclude: string) => {
    setExcludes(excludes.filter((e) => e !== exclude));
  };

  const onSubmit = async (data: ProjectForm) => {
    try {
      const project = await createProject({
        name: data.name,
        description: data.description,
        scope: {
          domains: domains.length > 0 ? domains : undefined,
          ips: ips.length > 0 ? ips : undefined,
          exclude: excludes.length > 0 ? excludes : undefined,
        },
      });
      toast({
        title: 'Project created',
        description: `${project.name} has been created successfully.`,
      });
      router.push(`/projects/${project.id}`);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create project. Please try again.',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="New Project"
        description="Create a new security testing project"
      />

      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Project Details */}
          <Card>
            <CardHeader>
              <CardTitle>Project Details</CardTitle>
              <CardDescription>
                Basic information about your project
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Project Name *</Label>
                <Input
                  id="name"
                  placeholder="e.g., Client Security Assessment"
                  {...register('name')}
                />
                {errors.name && (
                  <p className="text-sm text-destructive">{errors.name.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Brief description of the project scope and objectives..."
                  rows={4}
                  {...register('description')}
                />
                {errors.description && (
                  <p className="text-sm text-destructive">{errors.description.message}</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Scope Definition */}
          <Card>
            <CardHeader>
              <CardTitle>Scope Definition</CardTitle>
              <CardDescription>
                Define the targets and boundaries for testing
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="domains">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="domains">Domains</TabsTrigger>
                  <TabsTrigger value="ips">IPs/Networks</TabsTrigger>
                  <TabsTrigger value="exclude">Exclude</TabsTrigger>
                </TabsList>

                <TabsContent value="domains" className="space-y-4">
                  <div className="flex gap-2">
                    <Input
                      placeholder="example.com"
                      value={domainInput}
                      onChange={(e) => setDomainInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addDomain())}
                    />
                    <Button type="button" onClick={addDomain} variant="secondary">
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {domains.map((domain) => (
                      <Badge key={domain} variant="secondary" className="gap-1">
                        <Globe className="h-3 w-3" />
                        {domain}
                        <button
                          type="button"
                          onClick={() => removeDomain(domain)}
                          className="ml-1 hover:text-destructive"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                    {domains.length === 0 && (
                      <p className="text-sm text-muted-foreground">No domains added</p>
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="ips" className="space-y-4">
                  <div className="flex gap-2">
                    <Input
                      placeholder="192.168.1.0/24 or 10.0.0.1"
                      value={ipInput}
                      onChange={(e) => setIpInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addIp())}
                    />
                    <Button type="button" onClick={addIp} variant="secondary">
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {ips.map((ip) => (
                      <Badge key={ip} variant="secondary" className="gap-1">
                        <Network className="h-3 w-3" />
                        {ip}
                        <button
                          type="button"
                          onClick={() => removeIp(ip)}
                          className="ml-1 hover:text-destructive"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                    {ips.length === 0 && (
                      <p className="text-sm text-muted-foreground">No IPs/networks added</p>
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="exclude" className="space-y-4">
                  <div className="flex gap-2">
                    <Input
                      placeholder="out-of-scope.example.com"
                      value={excludeInput}
                      onChange={(e) => setExcludeInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addExclude())}
                    />
                    <Button type="button" onClick={addExclude} variant="secondary">
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {excludes.map((exclude) => (
                      <Badge key={exclude} variant="outline" className="gap-1 border-destructive text-destructive">
                        {exclude}
                        <button
                          type="button"
                          onClick={() => removeExclude(exclude)}
                          className="ml-1 hover:text-destructive"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                    {excludes.length === 0 && (
                      <p className="text-sm text-muted-foreground">No exclusions defined</p>
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>

        {/* Actions */}
        <div className="mt-6 flex justify-end gap-4">
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Project'
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
