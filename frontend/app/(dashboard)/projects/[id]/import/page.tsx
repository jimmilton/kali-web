'use client';

import { useState, useCallback, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Upload,
  FileUp,
  CheckCircle,
  AlertCircle,
  Loader2,
  FileText,
  ArrowLeft,
  Bug,
  Server,
  Key,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { PageHeader } from '@/components/layout/breadcrumbs';
import { useToast } from '@/components/ui/use-toast';
import { importApi, ImportFormat, ImportResult, projectsApi } from '@/lib/api';
import Link from 'next/link';

const FORMAT_ICONS: Record<string, React.ReactNode> = {
  nessus: <Bug className="h-6 w-6" />,
  burp: <Bug className="h-6 w-6" />,
  nuclei: <FileText className="h-6 w-6" />,
  nmap: <Server className="h-6 w-6" />,
};

const FORMAT_COLORS: Record<string, string> = {
  nessus: 'bg-green-500/10 text-green-500',
  burp: 'bg-orange-500/10 text-orange-500',
  nuclei: 'bg-purple-500/10 text-purple-500',
  nmap: 'bg-blue-500/10 text-blue-500',
};

export default function ImportPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const projectId = params.id as string;

  const [selectedFormat, setSelectedFormat] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);

  // Fetch project details
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
  });

  // Fetch available import formats
  const { data: formatsData, isLoading: formatsLoading } = useQuery({
    queryKey: ['import-formats'],
    queryFn: () => importApi.getFormats(),
  });

  const formats = formatsData?.formats || [];

  // Import mutation
  const importMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFormat || !selectedFile) {
        throw new Error('Please select a format and file');
      }
      return importApi.importFile(selectedFormat, projectId, selectedFile);
    },
    onSuccess: (result) => {
      setImportResult(result);
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: ['assets', projectId] });
      queryClient.invalidateQueries({ queryKey: ['vulnerabilities', projectId] });
      queryClient.invalidateQueries({ queryKey: ['credentials', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });

      if (result.success) {
        toast({
          title: 'Import successful',
          description: `Imported ${result.assets_created} assets, ${result.vulnerabilities_created} vulnerabilities`,
        });
      }
    },
    onError: (error: { detail?: string }) => {
      toast({
        variant: 'destructive',
        title: 'Import failed',
        description: error.detail || 'Failed to import file',
      });
    },
  });

  // Handle file selection
  const handleFileSelect = useCallback(
    (file: File) => {
      if (!selectedFormat) {
        // Try to auto-detect format from extension
        const ext = '.' + file.name.split('.').pop()?.toLowerCase();
        const matchingFormat = formats.find((f) => f.extensions.includes(ext));
        if (matchingFormat) {
          setSelectedFormat(matchingFormat.id);
        }
      }
      setSelectedFile(file);
    },
    [selectedFormat, formats]
  );

  // Drag and drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) {
        handleFileSelect(file);
      }
    },
    [handleFileSelect]
  );

  // Reset state
  const handleReset = () => {
    setSelectedFile(null);
    setImportResult(null);
  };

  // Get accepted extensions for current format
  const acceptedExtensions = selectedFormat
    ? formats.find((f) => f.id === selectedFormat)?.extensions.join(',')
    : formats.flatMap((f) => f.extensions).join(',');

  return (
    <div className="space-y-6">
      <PageHeader
        title="Import Scan Results"
        description={`Import external scan results into ${project?.name || 'this project'}`}
      >
        <Button variant="outline" asChild>
          <Link href={`/projects/${projectId}`}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Project
          </Link>
        </Button>
      </PageHeader>

      {/* Format Selection */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {formatsLoading ? (
          [...Array(4)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="pb-3">
                <div className="h-6 w-24 bg-muted rounded" />
              </CardHeader>
              <CardContent>
                <div className="h-4 w-full bg-muted rounded" />
              </CardContent>
            </Card>
          ))
        ) : (
          formats.map((format) => (
            <Card
              key={format.id}
              className={`cursor-pointer transition-all hover:border-primary ${
                selectedFormat === format.id ? 'border-primary ring-2 ring-primary/20' : ''
              }`}
              onClick={() => setSelectedFormat(format.id)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${FORMAT_COLORS[format.id] || 'bg-muted'}`}>
                    {FORMAT_ICONS[format.id] || <FileText className="h-6 w-6" />}
                  </div>
                  <div>
                    <CardTitle className="text-lg">{format.name}</CardTitle>
                    <div className="flex gap-1 mt-1">
                      {format.extensions.map((ext) => (
                        <Badge key={ext} variant="secondary" className="text-xs">
                          {ext}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <CardDescription>{format.description}</CardDescription>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* File Upload Area */}
      <Card>
        <CardHeader>
          <CardTitle>Upload File</CardTitle>
          <CardDescription>
            {selectedFormat
              ? `Select a ${formats.find((f) => f.id === selectedFormat)?.name} file to import`
              : 'Select a format above, then upload your scan results file'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {importResult ? (
            // Import Results
            <div className="space-y-4">
              <div
                className={`flex items-center gap-3 p-4 rounded-lg ${
                  importResult.success ? 'bg-green-500/10' : 'bg-red-500/10'
                }`}
              >
                {importResult.success ? (
                  <CheckCircle className="h-8 w-8 text-green-500" />
                ) : (
                  <AlertCircle className="h-8 w-8 text-red-500" />
                )}
                <div>
                  <p className="font-medium">
                    {importResult.success ? 'Import Completed Successfully' : 'Import Completed with Errors'}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Processed {selectedFile?.name}
                  </p>
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid gap-4 md:grid-cols-3">
                <div className="flex items-center gap-3 p-4 rounded-lg border">
                  <Server className="h-8 w-8 text-blue-500" />
                  <div>
                    <p className="text-2xl font-bold">{importResult.assets_created}</p>
                    <p className="text-sm text-muted-foreground">Assets Created</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-4 rounded-lg border">
                  <Bug className="h-8 w-8 text-red-500" />
                  <div>
                    <p className="text-2xl font-bold">{importResult.vulnerabilities_created}</p>
                    <p className="text-sm text-muted-foreground">Vulnerabilities Found</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-4 rounded-lg border">
                  <Key className="h-8 w-8 text-yellow-500" />
                  <div>
                    <p className="text-2xl font-bold">{importResult.credentials_created}</p>
                    <p className="text-sm text-muted-foreground">Credentials Found</p>
                  </div>
                </div>
              </div>

              {/* Errors */}
              {importResult.errors.length > 0 && (
                <div className="p-4 rounded-lg border border-destructive/50 bg-destructive/10">
                  <p className="font-medium text-destructive mb-2">
                    {importResult.errors.length} parsing errors occurred:
                  </p>
                  <ul className="text-sm space-y-1 text-muted-foreground">
                    {importResult.errors.slice(0, 5).map((error, i) => (
                      <li key={i}>{error}</li>
                    ))}
                    {importResult.errors.length > 5 && (
                      <li>...and {importResult.errors.length - 5} more</li>
                    )}
                  </ul>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3">
                <Button onClick={handleReset}>Import Another File</Button>
                <Button variant="outline" asChild>
                  <Link href={`/projects/${projectId}/vulnerabilities`}>
                    View Vulnerabilities
                  </Link>
                </Button>
                <Button variant="outline" asChild>
                  <Link href={`/projects/${projectId}/assets`}>View Assets</Link>
                </Button>
              </div>
            </div>
          ) : (
            // Upload Area
            <div
              className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                isDragging
                  ? 'border-primary bg-primary/5'
                  : selectedFile
                  ? 'border-green-500 bg-green-500/5'
                  : 'border-muted-foreground/25 hover:border-muted-foreground/50'
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <input
                type="file"
                accept={acceptedExtensions}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileSelect(file);
                }}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                disabled={importMutation.isPending}
              />

              {selectedFile ? (
                <div className="space-y-3">
                  <FileUp className="h-12 w-12 mx-auto text-green-500" />
                  <div>
                    <p className="font-medium">{selectedFile.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFile(null);
                    }}
                  >
                    Change File
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
                  <div>
                    <p className="font-medium">
                      {isDragging ? 'Drop file here' : 'Drag and drop or click to upload'}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {selectedFormat
                        ? `Accepts ${formats.find((f) => f.id === selectedFormat)?.extensions.join(', ')}`
                        : 'Select a format above first'}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Import Button */}
          {!importResult && selectedFile && (
            <div className="mt-4 flex justify-end">
              <Button
                onClick={() => importMutation.mutate()}
                disabled={!selectedFormat || !selectedFile || importMutation.isPending}
              >
                {importMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Importing...
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 h-4 w-4" />
                    Import File
                  </>
                )}
              </Button>
            </div>
          )}

          {importMutation.isPending && (
            <div className="mt-4 space-y-2">
              <Progress value={undefined} className="h-2" />
              <p className="text-sm text-center text-muted-foreground">
                Processing file, this may take a moment...
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
