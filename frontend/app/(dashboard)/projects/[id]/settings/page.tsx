'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Settings, Trash2, Users, Globe } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { PageHeader } from '@/components/layout/breadcrumbs';
import { useToast } from '@/components/ui/use-toast';
import { useProject } from '@/hooks/use-projects';

export default function ProjectSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const { project, isLoading } = useProject(projectId);
  const { toast } = useToast();
  const [saving, setSaving] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  if (isLoading) {
    return <SettingsSkeleton />;
  }

  if (!project) {
    return null;
  }

  const handleSave = async () => {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 1000));
    setSaving(false);
    toast({ title: 'Project settings saved' });
  };

  const handleDelete = async () => {
    toast({ title: 'Project deleted', variant: 'destructive' });
    router.push('/projects');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Project Settings"
        description={`Configure settings for ${project.name}`}
      />

      {/* General Settings */}
      <Card>
        <CardHeader>
          <CardTitle>General</CardTitle>
          <CardDescription>Basic project information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Project Name</Label>
            <Input id="name" defaultValue={project.name} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea id="description" defaultValue={project.description || ''} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="status">Status</Label>
            <Select defaultValue={project.status}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="archived">Archived</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </CardContent>
      </Card>

      {/* Scope Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            Scope
          </CardTitle>
          <CardDescription>Define target boundaries</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="domains">Domains (one per line)</Label>
            <Textarea
              id="domains"
              placeholder="example.com&#10;*.example.com"
              defaultValue={project.scope?.domains?.join('\n') || ''}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ips">IP Addresses/Ranges (one per line)</Label>
            <Textarea
              id="ips"
              placeholder="192.168.1.0/24&#10;10.0.0.1"
              defaultValue={project.scope?.ips?.join('\n') || ''}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="exclude">Exclusions (one per line)</Label>
            <Textarea
              id="exclude"
              placeholder="internal.example.com&#10;192.168.1.1"
              defaultValue={project.scope?.exclude?.join('\n') || ''}
            />
          </div>
          <Button onClick={handleSave} disabled={saving}>
            Update Scope
          </Button>
        </CardContent>
      </Card>

      {/* Team Members */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Team Members
          </CardTitle>
          <CardDescription>Manage project access</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <p className="font-medium">admin</p>
                <p className="text-sm text-muted-foreground">admin@example.com</p>
              </div>
              <Badge>Owner</Badge>
            </div>
            <Button variant="outline">
              <Users className="mr-2 h-4 w-4" />
              Invite Member
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="text-destructive">Danger Zone</CardTitle>
          <CardDescription>Irreversible actions</CardDescription>
        </CardHeader>
        <CardContent>
          <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Delete Project
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Delete Project</DialogTitle>
                <DialogDescription>
                  Are you sure you want to delete this project? This action cannot be undone.
                  All assets, vulnerabilities, and reports will be permanently deleted.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                  Cancel
                </Button>
                <Button variant="destructive" onClick={handleDelete}>
                  Delete Project
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>
    </div>
  );
}

function SettingsSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-48" />
        <Skeleton className="mt-2 h-4 w-64" />
      </div>
      {[...Array(3)].map((_, i) => (
        <Card key={i}>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48" />
          </CardHeader>
          <CardContent className="space-y-4">
            {[...Array(3)].map((_, j) => (
              <Skeleton key={j} className="h-10 w-full" />
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
