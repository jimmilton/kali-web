'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FileText,
  FileBarChart,
  ShieldCheck,
  Bug,
  Server,
  Wrench,
  Plus,
  Download,
  Trash2,
  Loader2,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
} from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { PageHeader } from '@/components/layout/breadcrumbs';
import { useToast } from '@/components/ui/use-toast';
import { useProject } from '@/hooks/use-projects';
import { CreateReportDialog } from '@/components/reports';
import { reportsApi, Report, ReportTemplateType } from '@/lib/api';

const TEMPLATE_ICONS: Record<ReportTemplateType, React.ReactNode> = {
  executive: <FileBarChart className="h-5 w-5" />,
  technical: <FileText className="h-5 w-5" />,
  compliance: <ShieldCheck className="h-5 w-5" />,
  vulnerability: <Bug className="h-5 w-5" />,
  asset: <Server className="h-5 w-5" />,
  custom: <Wrench className="h-5 w-5" />,
};

const TEMPLATE_COLORS: Record<ReportTemplateType, string> = {
  executive: 'bg-blue-500/10 text-blue-500',
  technical: 'bg-purple-500/10 text-purple-500',
  compliance: 'bg-green-500/10 text-green-500',
  vulnerability: 'bg-red-500/10 text-red-500',
  asset: 'bg-orange-500/10 text-orange-500',
  custom: 'bg-gray-500/10 text-gray-500',
};

const TEMPLATE_INFO: Record<ReportTemplateType, { name: string; description: string }> = {
  executive: { name: 'Executive Summary', description: 'High-level overview for stakeholders' },
  technical: { name: 'Technical Report', description: 'Detailed technical findings' },
  compliance: { name: 'Compliance Report', description: 'OWASP/PCI-DSS mapping' },
  vulnerability: { name: 'Vulnerability Report', description: 'Focused vulnerability listing' },
  asset: { name: 'Asset Inventory', description: 'Complete asset inventory' },
  custom: { name: 'Custom Report', description: 'User-defined sections' },
};

const STATUS_CONFIG = {
  pending: { icon: Clock, color: 'text-muted-foreground', label: 'Pending' },
  generating: { icon: Loader2, color: 'text-blue-500', label: 'Generating' },
  completed: { icon: CheckCircle, color: 'text-green-500', label: 'Completed' },
  failed: { icon: AlertCircle, color: 'text-red-500', label: 'Failed' },
};

function formatFileSize(bytes?: number): string {
  if (!bytes) return '-';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

export default function ProjectReportsPage() {
  const params = useParams();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const projectId = params.id as string;
  const { project, isLoading: projectLoading } = useProject(projectId);

  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<ReportTemplateType | undefined>();
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  // Fetch reports
  const { data: reportsData, isLoading: reportsLoading } = useQuery({
    queryKey: ['reports', projectId],
    queryFn: () => reportsApi.list(projectId),
    refetchInterval: (query) => {
      // Refetch more frequently if any reports are generating
      const data = query.state.data;
      const hasGenerating = data?.items?.some((r) => r.status === 'generating');
      return hasGenerating ? 3000 : false;
    },
  });

  const reports = reportsData?.items || [];

  // Generate mutation
  const generateMutation = useMutation({
    mutationFn: (id: string) => reportsApi.generate(id),
    onSuccess: () => {
      toast({ title: 'Report generation started' });
      queryClient.invalidateQueries({ queryKey: ['reports', projectId] });
    },
    onError: (error: { detail?: string }) => {
      toast({
        variant: 'destructive',
        title: 'Failed to generate report',
        description: error.detail || 'Could not start report generation',
      });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => reportsApi.delete(id),
    onSuccess: () => {
      toast({ title: 'Report deleted' });
      queryClient.invalidateQueries({ queryKey: ['reports', projectId] });
      setDeleteId(null);
    },
    onError: (error: { detail?: string }) => {
      toast({
        variant: 'destructive',
        title: 'Failed to delete report',
        description: error.detail || 'Could not delete report',
      });
    },
  });

  // Download handler
  const handleDownload = async (report: Report) => {
    if (report.status !== 'completed') return;

    setDownloadingId(report.id);
    try {
      const blob = await reportsApi.download(report.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title}.${report.format === 'markdown' ? 'md' : report.format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Download failed',
        description: 'Could not download the report',
      });
    } finally {
      setDownloadingId(null);
    }
  };

  // Template card click handler
  const handleTemplateClick = (template: ReportTemplateType) => {
    setSelectedTemplate(template);
    setCreateDialogOpen(true);
  };

  if (projectLoading || reportsLoading) {
    return <ReportsSkeleton />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        description={`Generated reports for ${project?.name || 'project'}`}
      >
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Generate Report
        </Button>
      </PageHeader>

      {/* Report Templates */}
      <div className="grid gap-4 md:grid-cols-3">
        {(['executive', 'technical', 'compliance'] as ReportTemplateType[]).map((templateType) => {
          const info = TEMPLATE_INFO[templateType];
          return (
            <Card
              key={templateType}
              className="cursor-pointer hover:border-primary transition-colors"
              onClick={() => handleTemplateClick(templateType)}
            >
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className={`p-3 rounded-lg ${TEMPLATE_COLORS[templateType]}`}>
                    {TEMPLATE_ICONS[templateType]}
                  </div>
                  <div>
                    <h3 className="font-semibold">{info.name}</h3>
                    <p className="text-sm text-muted-foreground">{info.description}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Reports List */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold">Generated Reports</h3>
        </CardHeader>
        <CardContent className="p-0">
          {reports.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <FileText className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold">No reports generated</h3>
              <p className="text-muted-foreground mt-1">
                Generate a report using one of the templates above
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Template</TableHead>
                  <TableHead>Format</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reports.map((report) => {
                  const statusConfig = STATUS_CONFIG[report.status];
                  const StatusIcon = statusConfig.icon;

                  return (
                    <TableRow key={report.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <div className={`p-1 rounded ${TEMPLATE_COLORS[report.template]}`}>
                            {TEMPLATE_ICONS[report.template]}
                          </div>
                          <span className="truncate max-w-[200px]">{report.title}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="capitalize">
                          {report.template}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{report.format.toUpperCase()}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          <StatusIcon
                            className={`h-4 w-4 ${statusConfig.color} ${
                              report.status === 'generating' ? 'animate-spin' : ''
                            }`}
                          />
                          <span className="text-sm">{statusConfig.label}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatFileSize(report.file_size)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(report.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          {report.status === 'completed' && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDownload(report)}
                              disabled={downloadingId === report.id}
                            >
                              {downloadingId === report.id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Download className="h-4 w-4" />
                              )}
                            </Button>
                          )}
                          {(report.status === 'pending' || report.status === 'failed') && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => generateMutation.mutate(report.id)}
                              disabled={generateMutation.isPending}
                            >
                              <RefreshCw className="h-4 w-4" />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDeleteId(report.id)}
                            disabled={report.status === 'generating'}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <CreateReportDialog
        open={createDialogOpen}
        onOpenChange={(open) => {
          setCreateDialogOpen(open);
          if (!open) setSelectedTemplate(undefined);
        }}
        projectId={projectId}
        initialTemplate={selectedTemplate}
      />

      {/* Delete Confirmation */}
      <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Report</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this report? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteId && deleteMutation.mutate(deleteId)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                'Delete'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function ReportsSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-32" />
        <Skeleton className="mt-2 h-4 w-64" />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {[...Array(3)].map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <Card>
        <CardContent className="p-6">
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
