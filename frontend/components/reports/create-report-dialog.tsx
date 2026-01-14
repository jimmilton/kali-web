'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FileText,
  FileBarChart,
  ShieldCheck,
  Bug,
  Server,
  Wrench,
  Loader2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/components/ui/use-toast';
import {
  reportsApi,
  ReportTemplateType,
  ReportFormatType,
  ReportTemplateInfo,
  CreateReportInput,
} from '@/lib/api';

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

const FORMAT_OPTIONS: { value: ReportFormatType; label: string; description: string }[] = [
  { value: 'pdf', label: 'PDF', description: 'Best for sharing and printing' },
  { value: 'docx', label: 'Word', description: 'Editable Microsoft Word document' },
  { value: 'html', label: 'HTML', description: 'Web-viewable format' },
  { value: 'markdown', label: 'Markdown', description: 'Plain text with formatting' },
  { value: 'json', label: 'JSON', description: 'Machine-readable data' },
];

const SEVERITY_OPTIONS = ['critical', 'high', 'medium', 'low', 'info'];

interface CreateReportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  initialTemplate?: ReportTemplateType;
}

export function CreateReportDialog({
  open,
  onOpenChange,
  projectId,
  initialTemplate,
}: CreateReportDialogProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Form state
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [template, setTemplate] = useState<ReportTemplateType>(initialTemplate || 'technical');
  const [format, setFormat] = useState<ReportFormatType>('pdf');
  const [includeEvidence, setIncludeEvidence] = useState(true);
  const [includeRemediation, setIncludeRemediation] = useState(true);
  const [includeReferences, setIncludeReferences] = useState(true);
  const [includeRawOutput, setIncludeRawOutput] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<string[]>([]);

  // Branding
  const [companyName, setCompanyName] = useState('');
  const [footerText, setFooterText] = useState('');

  // Fetch templates
  const { data: templates, isLoading: templatesLoading } = useQuery({
    queryKey: ['report-templates'],
    queryFn: () => reportsApi.getTemplates(),
    enabled: open,
  });

  // Reset form when opening with initial template
  useEffect(() => {
    if (open) {
      setTemplate(initialTemplate || 'technical');
      // Set default title based on template
      const templateInfo = templates?.find((t) => t.id === (initialTemplate || 'technical'));
      if (templateInfo) {
        setTitle(`${templateInfo.name} - ${new Date().toLocaleDateString()}`);
      }
    }
  }, [open, initialTemplate, templates]);

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async () => {
      const data: CreateReportInput = {
        project_id: projectId,
        title: title || `Report - ${new Date().toLocaleDateString()}`,
        description: description || undefined,
        template,
        format,
        content: {
          include_evidence: includeEvidence,
          include_remediation: includeRemediation,
          include_references: includeReferences,
          include_raw_output: includeRawOutput,
          severity_filter: severityFilter.length > 0 ? severityFilter : undefined,
        },
        branding: {
          company_name: companyName || undefined,
          footer_text: footerText || undefined,
        },
      };
      return reportsApi.create(data);
    },
    onSuccess: async (report) => {
      // Automatically trigger generation
      try {
        await reportsApi.generate(report.id);
        toast({
          title: 'Report created',
          description: 'Your report is being generated. You will be notified when it\'s ready.',
        });
      } catch {
        toast({
          title: 'Report created',
          description: 'Report created but generation failed to start. You can trigger it manually.',
        });
      }

      queryClient.invalidateQueries({ queryKey: ['reports', projectId] });
      onOpenChange(false);
      resetForm();
    },
    onError: (error: { detail?: string }) => {
      toast({
        variant: 'destructive',
        title: 'Failed to create report',
        description: error.detail || 'Could not create report',
      });
    },
  });

  const resetForm = () => {
    setTitle('');
    setDescription('');
    setTemplate('technical');
    setFormat('pdf');
    setIncludeEvidence(true);
    setIncludeRemediation(true);
    setIncludeReferences(true);
    setIncludeRawOutput(false);
    setSeverityFilter([]);
    setCompanyName('');
    setFooterText('');
    setShowAdvanced(false);
  };

  const toggleSeverity = (severity: string) => {
    setSeverityFilter((prev) =>
      prev.includes(severity)
        ? prev.filter((s) => s !== severity)
        : [...prev, severity]
    );
  };

  const selectedTemplateInfo = templates?.find((t) => t.id === template);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Generate Report</DialogTitle>
          <DialogDescription>
            Create a new report for this project. Choose a template and customize the options.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Template Selection */}
          <div className="space-y-3">
            <Label>Report Template</Label>
            <div className="grid grid-cols-2 gap-3">
              {templatesLoading ? (
                [...Array(6)].map((_, i) => (
                  <div key={i} className="h-20 bg-muted animate-pulse rounded-lg" />
                ))
              ) : (
                templates?.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setTemplate(t.id)}
                    className={`flex items-start gap-3 p-3 rounded-lg border text-left transition-all ${
                      template === t.id
                        ? 'border-primary ring-2 ring-primary/20'
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    <div className={`p-2 rounded-lg ${TEMPLATE_COLORS[t.id]}`}>
                      {TEMPLATE_ICONS[t.id]}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm">{t.name}</p>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {t.description}
                      </p>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Basic Info */}
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="title">Report Title</Label>
              <Input
                id="title"
                placeholder={`${selectedTemplateInfo?.name || 'Report'} - ${new Date().toLocaleDateString()}`}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="format">Output Format</Label>
              <Select value={format} onValueChange={(v) => setFormat(v as ReportFormatType)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FORMAT_OPTIONS.map((f) => (
                    <SelectItem key={f.value} value={f.value}>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{f.label}</span>
                        <span className="text-xs text-muted-foreground">- {f.description}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description (optional)</Label>
            <Textarea
              id="description"
              placeholder="Add any notes or context for this report..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>

          {/* Content Options */}
          <div className="space-y-4">
            <Label>Content Options</Label>
            <div className="grid gap-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Include Evidence</p>
                  <p className="text-xs text-muted-foreground">
                    Screenshots and proof-of-concept details
                  </p>
                </div>
                <Switch checked={includeEvidence} onCheckedChange={setIncludeEvidence} />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Include Remediation</p>
                  <p className="text-xs text-muted-foreground">
                    Fix recommendations for vulnerabilities
                  </p>
                </div>
                <Switch checked={includeRemediation} onCheckedChange={setIncludeRemediation} />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Include References</p>
                  <p className="text-xs text-muted-foreground">
                    CVE, CWE, and external links
                  </p>
                </div>
                <Switch checked={includeReferences} onCheckedChange={setIncludeReferences} />
              </div>
            </div>
          </div>

          {/* Severity Filter */}
          <div className="space-y-3">
            <Label>Filter by Severity</Label>
            <p className="text-xs text-muted-foreground">
              Leave empty to include all severities
            </p>
            <div className="flex flex-wrap gap-2">
              {SEVERITY_OPTIONS.map((severity) => (
                <Badge
                  key={severity}
                  variant={severityFilter.includes(severity) ? 'default' : 'outline'}
                  className="cursor-pointer capitalize"
                  onClick={() => toggleSeverity(severity)}
                >
                  {severity}
                </Badge>
              ))}
            </div>
          </div>

          {/* Advanced Options */}
          <div className="space-y-4">
            <Button
              type="button"
              variant="ghost"
              className="w-full justify-between"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              Advanced Options
              {showAdvanced ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
            {showAdvanced && (
              <div className="space-y-4 pt-2">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Include Raw Tool Output</p>
                    <p className="text-xs text-muted-foreground">
                      Append raw scan output in appendix
                    </p>
                  </div>
                  <Switch checked={includeRawOutput} onCheckedChange={setIncludeRawOutput} />
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="companyName">Company Name (Branding)</Label>
                    <Input
                      id="companyName"
                      placeholder="Your Company Name"
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="footerText">Footer Text</Label>
                    <Input
                      id="footerText"
                      placeholder="Confidential - Do Not Distribute"
                      value={footerText}
                      onChange={(e) => setFooterText(e.target.value)}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <FileText className="mr-2 h-4 w-4" />
                Generate Report
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
