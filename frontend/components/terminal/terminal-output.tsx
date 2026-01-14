'use client';

import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import { JobOutputEvent } from '@/lib/socket';

interface TerminalOutputProps {
  outputs: JobOutputEvent[];
  onInput?: (input: string) => void;
  className?: string;
}

export function TerminalOutput({ outputs, onInput, className }: TerminalOutputProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [inputValue, setInputValue] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto-scroll to bottom when new output arrives
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [outputs, autoScroll]);

  // Detect manual scroll to disable auto-scroll
  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setAutoScroll(isAtBottom);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && onInput && inputValue.trim()) {
      onInput(inputValue);
      setInputValue('');
    }
  };

  const handleContainerClick = () => {
    inputRef.current?.focus();
  };

  return (
    <div
      className={cn(
        'h-full bg-black text-green-400 font-mono text-sm flex flex-col',
        className
      )}
      onClick={handleContainerClick}
    >
      <div
        ref={containerRef}
        className="flex-1 overflow-auto p-4 space-y-1"
        onScroll={handleScroll}
      >
        {outputs.length === 0 ? (
          <div className="text-gray-500 italic">Waiting for output...</div>
        ) : (
          outputs.map((output, index) => (
            <TerminalLine key={index} output={output} />
          ))
        )}
      </div>

      {onInput && (
        <div className="border-t border-gray-700 p-2 flex items-center gap-2">
          <span className="text-gray-500">$</span>
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-transparent border-none outline-none text-green-400"
            placeholder="Type command and press Enter..."
          />
        </div>
      )}
    </div>
  );
}

function TerminalLine({ output }: { output: JobOutputEvent }) {
  const content = parseAnsi(output.content);

  const lineClass = cn({
    'text-red-400': output.output_type === 'stderr',
    'text-blue-400': output.output_type === 'system',
    'text-green-400': output.output_type === 'stdout',
  });

  return (
    <div className={cn('whitespace-pre-wrap break-all', lineClass)}>
      {content}
    </div>
  );
}

// Simple ANSI escape code parser
function parseAnsi(text: string): React.ReactNode {
  // Remove common ANSI escape sequences and return plain text
  // In a production app, you'd use a library like ansi-to-react or xterm.js
  const cleaned = text
    .replace(/\x1B\[[0-9;]*[A-Za-z]/g, '') // Remove escape sequences
    .replace(/\x1B\]0;[^\x07]*\x07/g, '')  // Remove title sequences
    .replace(/\r/g, '');                     // Remove carriage returns

  return cleaned;
}
