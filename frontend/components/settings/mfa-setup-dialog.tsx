'use client';

import { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { Shield, Copy, Check, Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/components/ui/use-toast';
import { authApi, MFASetupResponse } from '@/lib/api';

interface MFASetupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

type Step = 'setup' | 'verify' | 'backup';

export function MFASetupDialog({ open, onOpenChange, onSuccess }: MFASetupDialogProps) {
  const { toast } = useToast();
  const [step, setStep] = useState<Step>('setup');
  const [loading, setLoading] = useState(false);
  const [setupData, setSetupData] = useState<MFASetupResponse | null>(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [copiedBackup, setCopiedBackup] = useState(false);

  const handleSetup = async () => {
    setLoading(true);
    try {
      const data = await authApi.mfaSetup();
      setSetupData(data);
      setStep('verify');
    } catch (error: unknown) {
      const err = error as { detail?: string };
      toast({
        variant: 'destructive',
        title: 'Setup failed',
        description: err.detail || 'Failed to initialize MFA setup',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    if (verifyCode.length !== 6) {
      toast({
        variant: 'destructive',
        title: 'Invalid code',
        description: 'Please enter a 6-digit code',
      });
      return;
    }

    setLoading(true);
    try {
      await authApi.mfaEnable(verifyCode);
      setStep('backup');
      toast({
        title: 'MFA enabled',
        description: 'Two-factor authentication has been enabled',
      });
    } catch (error: unknown) {
      const err = error as { detail?: string };
      toast({
        variant: 'destructive',
        title: 'Verification failed',
        description: err.detail || 'Invalid verification code',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCopySecret = () => {
    if (setupData?.secret) {
      navigator.clipboard.writeText(setupData.secret);
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 2000);
    }
  };

  const handleCopyBackupCodes = () => {
    if (setupData?.backup_codes) {
      navigator.clipboard.writeText(setupData.backup_codes.join('\n'));
      setCopiedBackup(true);
      setTimeout(() => setCopiedBackup(false), 2000);
    }
  };

  const handleClose = () => {
    if (step === 'backup') {
      onSuccess();
    }
    onOpenChange(false);
    // Reset state after dialog closes
    setTimeout(() => {
      setStep('setup');
      setSetupData(null);
      setVerifyCode('');
    }, 200);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            {step === 'setup' && 'Enable Two-Factor Authentication'}
            {step === 'verify' && 'Scan QR Code'}
            {step === 'backup' && 'Save Backup Codes'}
          </DialogTitle>
          <DialogDescription>
            {step === 'setup' &&
              'Add an extra layer of security to your account using an authenticator app.'}
            {step === 'verify' &&
              'Scan the QR code with your authenticator app, then enter the code to verify.'}
            {step === 'backup' &&
              'Save these backup codes in a secure location. You can use them if you lose access to your authenticator.'}
          </DialogDescription>
        </DialogHeader>

        {step === 'setup' && (
          <div className="space-y-4 pt-4">
            <p className="text-sm text-muted-foreground">
              You will need an authenticator app like Google Authenticator, Authy, or 1Password to
              generate verification codes.
            </p>
            <Button onClick={handleSetup} disabled={loading} className="w-full">
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Setting up...
                </>
              ) : (
                'Begin Setup'
              )}
            </Button>
          </div>
        )}

        {step === 'verify' && setupData && (
          <div className="space-y-4 pt-4">
            <div className="flex justify-center rounded-lg bg-white p-4">
              <QRCodeSVG value={setupData.qr_code} size={200} />
            </div>

            <div className="space-y-2">
              <Label className="text-sm text-muted-foreground">
                Or enter this secret manually:
              </Label>
              <div className="flex gap-2">
                <Input
                  value={setupData.secret}
                  readOnly
                  className="font-mono text-sm"
                />
                <Button variant="outline" size="icon" onClick={handleCopySecret}>
                  {copiedSecret ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="verify-code">Enter verification code</Label>
              <Input
                id="verify-code"
                placeholder="000000"
                value={verifyCode}
                onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                maxLength={6}
                className="font-mono text-center text-lg tracking-widest"
              />
            </div>

            <Button onClick={handleVerify} disabled={loading || verifyCode.length !== 6} className="w-full">
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Verifying...
                </>
              ) : (
                'Verify and Enable'
              )}
            </Button>
          </div>
        )}

        {step === 'backup' && setupData && (
          <div className="space-y-4 pt-4">
            <div className="rounded-lg border bg-muted/50 p-4">
              <div className="grid grid-cols-2 gap-2 font-mono text-sm">
                {setupData.backup_codes.map((code, i) => (
                  <div key={i} className="rounded bg-background p-2 text-center">
                    {code}
                  </div>
                ))}
              </div>
            </div>

            <Button variant="outline" onClick={handleCopyBackupCodes} className="w-full">
              {copiedBackup ? (
                <>
                  <Check className="mr-2 h-4 w-4" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="mr-2 h-4 w-4" />
                  Copy Backup Codes
                </>
              )}
            </Button>

            <p className="text-xs text-muted-foreground">
              Each backup code can only be used once. Store them securely.
            </p>

            <Button onClick={handleClose} className="w-full">
              Done
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
