'use client';

import { useState } from 'react';
import { ShieldOff, Loader2 } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/components/ui/use-toast';
import { authApi } from '@/lib/api';

interface MFADisableDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function MFADisableDialog({ open, onOpenChange, onSuccess }: MFADisableDialogProps) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [code, setCode] = useState('');

  const handleDisable = async () => {
    if (code.length !== 6) {
      toast({
        variant: 'destructive',
        title: 'Invalid code',
        description: 'Please enter a 6-digit code',
      });
      return;
    }

    setLoading(true);
    try {
      await authApi.mfaDisable(code);
      toast({
        title: 'MFA disabled',
        description: 'Two-factor authentication has been disabled',
      });
      onSuccess();
      onOpenChange(false);
      setCode('');
    } catch (error: unknown) {
      const err = error as { detail?: string };
      toast({
        variant: 'destructive',
        title: 'Failed to disable MFA',
        description: err.detail || 'Invalid verification code',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    onOpenChange(false);
    setCode('');
  };

  return (
    <AlertDialog open={open} onOpenChange={handleClose}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <ShieldOff className="h-5 w-5 text-destructive" />
            Disable Two-Factor Authentication
          </AlertDialogTitle>
          <AlertDialogDescription>
            This will make your account less secure. You will no longer need a verification code to
            sign in.
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="space-y-2 py-4">
          <Label htmlFor="disable-code">Enter verification code to confirm</Label>
          <Input
            id="disable-code"
            placeholder="000000"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            maxLength={6}
            className="font-mono text-center text-lg tracking-widest"
          />
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel disabled={loading}>Cancel</AlertDialogCancel>
          <Button
            variant="destructive"
            onClick={handleDisable}
            disabled={loading || code.length !== 6}
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Disabling...
              </>
            ) : (
              'Disable MFA'
            )}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
