'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useForm, Controller } from 'react-hook-form';
import {
  Play,
  Terminal,
  Copy,
  ChevronDown,
  Loader2,
  Info,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { PageHeader } from '@/components/layout/breadcrumbs';
import { useToast } from '@/components/ui/use-toast';
import { toolsApi, jobsApi, Tool, ToolParameter } from '@/lib/api';
import { useProjects } from '@/hooks/use-projects';
import { cn } from '@/lib/utils';

export default function ToolConfigPage() {
  const params = useParams();
  const router = useRouter();
  const slug = params.slug as string;
  const { toast } = useToast();

  const [tool, setTool] = useState<Tool | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [commandPreview, setCommandPreview] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);

  const { projects } = useProjects();
  const { control, handleSubmit, watch, setValue, formState: { errors } } = useForm<Record<string, unknown>>();

  const watchedValues = watch();

  useEffect(() => {
    const fetchTool = async () => {
      try {
        const data = await toolsApi.get(slug);
        setTool(data);

        // Set default values
        data.parameters.forEach((param) => {
          if (param.default !== undefined) {
            setValue(param.name, param.default);
          }
        });
      } catch (error) {
        console.error('Failed to fetch tool:', error);
        toast({
          title: 'Error',
          description: 'Failed to load tool configuration',
          variant: 'destructive',
        });
      } finally {
        setIsLoading(false);
      }
    };
    fetchTool();
  }, [slug, setValue, toast]);

  // Update command preview
  useEffect(() => {
    if (!tool) return;

    const updatePreview = async () => {
      setPreviewLoading(true);
      try {
        const response = await toolsApi.preview(slug, watchedValues);
        setCommandPreview(response.command);
      } catch {
        setCommandPreview('Unable to generate preview');
      } finally {
        setPreviewLoading(false);
      }
    };

    const timer = setTimeout(updatePreview, 500);
    return () => clearTimeout(timer);
  }, [tool, slug, watchedValues]);

  const onSubmit = async (data: Record<string, unknown>) => {
    if (!data.project_id) {
      toast({
        title: 'Error',
        description: 'Please select a project',
        variant: 'destructive',
      });
      return;
    }

    setIsSubmitting(true);
    try {
      const job = await jobsApi.create({
        project_id: data.project_id as string,
        tool_name: slug,
        parameters: Object.fromEntries(
          Object.entries(data).filter(([key]) => key !== 'project_id')
        ),
      });
      toast({
        title: 'Job started',
        description: 'Tool execution has been queued',
      });
      router.push(`/jobs/${job.id}`);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to start tool execution',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyCommand = () => {
    navigator.clipboard.writeText(commandPreview);
    toast({
      title: 'Copied',
      description: 'Command copied to clipboard',
    });
  };

  if (isLoading) {
    return <ToolSkeleton />;
  }

  if (!tool) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <h2 className="text-xl font-semibold">Tool not found</h2>
        <Button className="mt-4" asChild>
          <a href="/tools">Back to Tools</a>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={tool.name}
        description={tool.description}
      >
        <Badge variant="outline">{tool.category}</Badge>
      </PageHeader>

      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Configuration */}
          <div className="lg:col-span-2 space-y-6">
            {/* Project Selection */}
            <Card>
              <CardHeader>
                <CardTitle>Target Project</CardTitle>
                <CardDescription>
                  Select the project to run this tool against
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Controller
                  name="project_id"
                  control={control}
                  rules={{ required: 'Project is required' }}
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value as string}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a project" />
                      </SelectTrigger>
                      <SelectContent>
                        {projects.map((project) => (
                          <SelectItem key={project.id} value={project.id}>
                            {project.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
                {errors.project_id && (
                  <p className="mt-1 text-sm text-destructive">
                    {errors.project_id.message as string}
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Tool Parameters */}
            <Card>
              <CardHeader>
                <CardTitle>Parameters</CardTitle>
                <CardDescription>
                  Configure tool options and settings
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {tool.parameters.map((param) => (
                  <ParameterInput
                    key={param.name}
                    parameter={param}
                    control={control}
                    errors={errors}
                  />
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Command Preview */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-base">Command Preview</CardTitle>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={copyCommand}
                  disabled={!commandPreview}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </CardHeader>
              <CardContent>
                <div className="relative rounded-lg bg-muted p-4 font-mono text-sm">
                  {previewLoading ? (
                    <Skeleton className="h-4 w-full" />
                  ) : (
                    <code className="break-all">{commandPreview || 'Configure parameters to see preview'}</code>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Run Button */}
            <Card>
              <CardContent className="pt-6">
                <Button
                  type="submit"
                  className="w-full"
                  size="lg"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Starting...
                    </>
                  ) : (
                    <>
                      <Play className="mr-2 h-4 w-4" />
                      Run {tool.name}
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* Tool Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">About this tool</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Category</span>
                  <Badge variant="secondary">{tool.category}</Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Docker Image</span>
                  <span className="font-mono text-xs">{tool.docker_image}</span>
                </div>
                {tool.output_parsers && tool.output_parsers.length > 0 && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Auto-parsing</span>
                    <Badge variant="outline">Enabled</Badge>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </form>
    </div>
  );
}

interface ParameterInputProps {
  parameter: ToolParameter;
  control: any;
  errors: any;
}

function ParameterInput({ parameter, control, errors }: ParameterInputProps) {
  const isRequired = parameter.required;
  const error = errors[parameter.name];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label htmlFor={parameter.name} className="flex items-center gap-1">
          {parameter.label}
          {isRequired && <span className="text-destructive">*</span>}
        </Label>
        {parameter.description && (
          <span className="text-xs text-muted-foreground">
            {parameter.description}
          </span>
        )}
      </div>

      <Controller
        name={parameter.name}
        control={control}
        rules={{ required: isRequired ? `${parameter.label} is required` : false }}
        render={({ field }) => {
          switch (parameter.type) {
            case 'boolean':
              return (
                <div className="flex items-center gap-2">
                  <Switch
                    checked={field.value as boolean}
                    onCheckedChange={field.onChange}
                  />
                  <span className="text-sm text-muted-foreground">
                    {field.value ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
              );

            case 'select':
              return (
                <Select onValueChange={field.onChange} value={field.value as string}>
                  <SelectTrigger>
                    <SelectValue placeholder={`Select ${parameter.label.toLowerCase()}`} />
                  </SelectTrigger>
                  <SelectContent>
                    {parameter.options?.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              );

            case 'textarea':
              return (
                <Textarea
                  {...field}
                  value={field.value as string || ''}
                  placeholder={parameter.placeholder || `Enter ${parameter.label.toLowerCase()}`}
                  rows={4}
                />
              );

            case 'number':
              return (
                <Input
                  {...field}
                  type="number"
                  value={field.value as number || ''}
                  onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : '')}
                  placeholder={parameter.placeholder || `Enter ${parameter.label.toLowerCase()}`}
                  min={parameter.validation?.min}
                  max={parameter.validation?.max}
                />
              );

            default:
              return (
                <Input
                  {...field}
                  value={field.value as string || ''}
                  placeholder={parameter.placeholder || `Enter ${parameter.label.toLowerCase()}`}
                />
              );
          }
        }}
      />

      {error && (
        <p className="text-sm text-destructive">{error.message}</p>
      )}
    </div>
  );
}

function ToolSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-48" />
        <Skeleton className="mt-2 h-4 w-96" />
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <Skeleton className="h-5 w-32" />
            </CardHeader>
            <CardContent className="space-y-4">
              {[...Array(4)].map((_, i) => (
                <div key={i}>
                  <Skeleton className="h-4 w-24 mb-2" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <Skeleton className="h-5 w-32" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-24 w-full" />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
