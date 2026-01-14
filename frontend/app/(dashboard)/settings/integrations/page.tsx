'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  MessageSquare,
  Send,
  Ticket,
  Plus,
  Trash2,
  Settings,
  CheckCircle,
  XCircle,
  Loader2,
  Eye,
  EyeOff,
  TestTube,
  ArrowLeft,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PageHeader } from '@/components/layout/breadcrumbs';
import { useToast } from '@/components/ui/use-toast';
import Link from 'next/link';

// Integration type definitions
interface Integration {
  id: string;
  name: string;
  type: 'slack' | 'discord' | 'jira';
  enabled: boolean;
  config: Record<string, string>;
  lastTest?: { success: boolean; message: string; at: string };
}

const INTEGRATION_TYPES = {
  slack: {
    name: 'Slack',
    icon: MessageSquare,
    color: 'bg-[#4A154B]/10 text-[#4A154B]',
    description: 'Send notifications to Slack channels via webhooks',
    fields: [
      { name: 'webhook_url', label: 'Webhook URL', type: 'url', placeholder: 'https://hooks.slack.com/services/...' },
    ],
  },
  discord: {
    name: 'Discord',
    icon: Send,
    color: 'bg-[#5865F2]/10 text-[#5865F2]',
    description: 'Send notifications to Discord channels via webhooks',
    fields: [
      { name: 'webhook_url', label: 'Webhook URL', type: 'url', placeholder: 'https://discord.com/api/webhooks/...' },
    ],
  },
  jira: {
    name: 'Jira',
    icon: Ticket,
    color: 'bg-[#0052CC]/10 text-[#0052CC]',
    description: 'Create issues in Jira for vulnerabilities',
    fields: [
      { name: 'base_url', label: 'Jira URL', type: 'url', placeholder: 'https://your-domain.atlassian.net' },
      { name: 'email', label: 'Email', type: 'email', placeholder: 'your-email@company.com' },
      { name: 'api_token', label: 'API Token', type: 'password', placeholder: 'Your Jira API token' },
      { name: 'project_key', label: 'Project Key', type: 'text', placeholder: 'SEC' },
    ],
  },
};

// Mock data - in real implementation, this would come from API
const mockIntegrations: Integration[] = [];

export default function IntegrationsPage() {
  const { toast } = useToast();
  const [integrations, setIntegrations] = useState<Integration[]>(mockIntegrations);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingIntegration, setEditingIntegration] = useState<Integration | null>(null);
  const [selectedType, setSelectedType] = useState<'slack' | 'discord' | 'jira'>('slack');
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});

  const [formData, setFormData] = useState<Record<string, string>>({
    name: '',
    webhook_url: '',
    base_url: '',
    email: '',
    api_token: '',
    project_key: '',
  });

  const handleOpenDialog = (integration?: Integration) => {
    if (integration) {
      setEditingIntegration(integration);
      setSelectedType(integration.type);
      setFormData({
        name: integration.name,
        ...integration.config,
      });
    } else {
      setEditingIntegration(null);
      setSelectedType('slack');
      setFormData({
        name: '',
        webhook_url: '',
        base_url: '',
        email: '',
        api_token: '',
        project_key: '',
      });
    }
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);

    // Simulate API call
    await new Promise((r) => setTimeout(r, 1000));

    const typeConfig = INTEGRATION_TYPES[selectedType];
    const config: Record<string, string> = {};
    typeConfig.fields.forEach((field) => {
      if (formData[field.name]) {
        config[field.name] = formData[field.name];
      }
    });

    if (editingIntegration) {
      // Update existing
      setIntegrations((prev) =>
        prev.map((i) =>
          i.id === editingIntegration.id
            ? { ...i, name: formData.name, config }
            : i
        )
      );
      toast({ title: 'Integration updated' });
    } else {
      // Create new
      const newIntegration: Integration = {
        id: Date.now().toString(),
        name: formData.name || typeConfig.name,
        type: selectedType,
        enabled: true,
        config,
      };
      setIntegrations((prev) => [...prev, newIntegration]);
      toast({ title: 'Integration added' });
    }

    setSaving(false);
    setDialogOpen(false);
  };

  const handleDelete = async (id: string) => {
    setIntegrations((prev) => prev.filter((i) => i.id !== id));
    toast({ title: 'Integration removed' });
  };

  const handleToggle = async (id: string, enabled: boolean) => {
    setIntegrations((prev) =>
      prev.map((i) => (i.id === id ? { ...i, enabled } : i))
    );
    toast({ title: enabled ? 'Integration enabled' : 'Integration disabled' });
  };

  const handleTest = async (integration: Integration) => {
    setTesting(integration.id);

    // Simulate API test call
    await new Promise((r) => setTimeout(r, 2000));

    const success = Math.random() > 0.3; // Simulated success/failure

    setIntegrations((prev) =>
      prev.map((i) =>
        i.id === integration.id
          ? {
              ...i,
              lastTest: {
                success,
                message: success ? 'Connection successful' : 'Failed to connect',
                at: new Date().toISOString(),
              },
            }
          : i
      )
    );

    toast({
      title: success ? 'Test successful' : 'Test failed',
      description: success ? 'Connection is working' : 'Could not connect to the service',
      variant: success ? 'default' : 'destructive',
    });

    setTesting(null);
  };

  const toggleSecretVisibility = (fieldName: string) => {
    setShowSecrets((prev) => ({ ...prev, [fieldName]: !prev[fieldName] }));
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Integrations"
        description="Connect external services for notifications and issue tracking"
      >
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link href="/settings">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Settings
            </Link>
          </Button>
          <Button onClick={() => handleOpenDialog()}>
            <Plus className="mr-2 h-4 w-4" />
            Add Integration
          </Button>
        </div>
      </PageHeader>

      {/* Integration Types Overview */}
      <div className="grid gap-4 md:grid-cols-3">
        {Object.entries(INTEGRATION_TYPES).map(([type, config]) => {
          const Icon = config.icon;
          const count = integrations.filter((i) => i.type === type).length;

          return (
            <Card key={type}>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${config.color}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">{config.name}</CardTitle>
                    <Badge variant="secondary">{count} configured</Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <CardDescription>{config.description}</CardDescription>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Configured Integrations */}
      <Card>
        <CardHeader>
          <CardTitle>Configured Integrations</CardTitle>
          <CardDescription>
            Manage your connected services and notification channels
          </CardDescription>
        </CardHeader>
        <CardContent>
          {integrations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Settings className="h-12 w-12 text-muted-foreground/50 mb-4" />
              <p className="text-lg font-medium">No integrations configured</p>
              <p className="text-sm text-muted-foreground mb-4">
                Add an integration to receive notifications for vulnerabilities and job completions
              </p>
              <Button onClick={() => handleOpenDialog()}>
                <Plus className="mr-2 h-4 w-4" />
                Add Your First Integration
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {integrations.map((integration) => {
                const typeConfig = INTEGRATION_TYPES[integration.type];
                const Icon = typeConfig.icon;

                return (
                  <div
                    key={integration.id}
                    className="flex items-center justify-between p-4 rounded-lg border"
                  >
                    <div className="flex items-center gap-4">
                      <div className={`p-2 rounded-lg ${typeConfig.color}`}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium">{integration.name}</p>
                          <Badge variant="outline">{typeConfig.name}</Badge>
                          {integration.lastTest && (
                            <Badge
                              variant={integration.lastTest.success ? 'default' : 'destructive'}
                            >
                              {integration.lastTest.success ? (
                                <CheckCircle className="mr-1 h-3 w-3" />
                              ) : (
                                <XCircle className="mr-1 h-3 w-3" />
                              )}
                              {integration.lastTest.success ? 'Connected' : 'Failed'}
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {integration.config.webhook_url
                            ? `Webhook: ${integration.config.webhook_url.substring(0, 50)}...`
                            : integration.config.base_url
                            ? `URL: ${integration.config.base_url}`
                            : 'Configured'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Switch
                        checked={integration.enabled}
                        onCheckedChange={(checked) => handleToggle(integration.id, checked)}
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTest(integration)}
                        disabled={testing === integration.id}
                      >
                        {testing === integration.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <TestTube className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleOpenDialog(integration)}
                      >
                        <Settings className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDelete(integration.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingIntegration ? 'Edit Integration' : 'Add Integration'}
            </DialogTitle>
            <DialogDescription>
              {editingIntegration
                ? 'Update the integration settings'
                : 'Configure a new integration to receive notifications'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {!editingIntegration && (
              <div className="space-y-2">
                <Label>Integration Type</Label>
                <Select
                  value={selectedType}
                  onValueChange={(v) => setSelectedType(v as 'slack' | 'discord' | 'jira')}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(INTEGRATION_TYPES).map(([type, config]) => (
                      <SelectItem key={type} value={type}>
                        <div className="flex items-center gap-2">
                          <config.icon className="h-4 w-4" />
                          {config.name}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                placeholder={`My ${INTEGRATION_TYPES[selectedType].name} Integration`}
                value={formData.name}
                onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
              />
            </div>

            {INTEGRATION_TYPES[selectedType].fields.map((field) => (
              <div key={field.name} className="space-y-2">
                <Label htmlFor={field.name}>{field.label}</Label>
                <div className="relative">
                  <Input
                    id={field.name}
                    type={
                      field.type === 'password'
                        ? showSecrets[field.name]
                          ? 'text'
                          : 'password'
                        : field.type
                    }
                    placeholder={field.placeholder}
                    value={formData[field.name] || ''}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, [field.name]: e.target.value }))
                    }
                  />
                  {field.type === 'password' && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 h-full px-3"
                      onClick={() => toggleSecretVisibility(field.name)}
                    >
                      {showSecrets[field.name] ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Integration'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
