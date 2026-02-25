// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Hafif, bagimliliksiz Markdown renderer.
// Chat yanitlarindaki **bold**, `code`, _italic_, ayiricilar ve listeleri parse eder.

import React from 'react';

interface MarkdownRendererProps {
  text: string;
}

/**
 * Satır içindeki inline Markdown'i JSX element array'ine donusturur.
 * Desteklenen: **bold**, `code`, _italic_
 */
function parseInline(text: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  // Sira: code > bold > italic
  // Regex: `code` | **bold** | _italic_
  const regex = /(`[^`]+`)|(\*\*[^*]+\*\*)|(_[^_]+_)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    // Onceki duz metin
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }

    const full = match[0];

    if (full.startsWith('`')) {
      // Code
      const content = full.slice(1, -1);
      nodes.push(
        <code
          key={`c-${match.index}`}
          className="bg-surface-800 text-neon-cyan px-1.5 py-0.5 rounded text-xs font-mono"
        >
          {content}
        </code>
      );
    } else if (full.startsWith('**')) {
      // Bold
      const content = full.slice(2, -2);
      nodes.push(
        <strong key={`b-${match.index}`} className="font-semibold text-white">
          {content}
        </strong>
      );
    } else if (full.startsWith('_') && full.endsWith('_')) {
      // Italic
      const content = full.slice(1, -1);
      nodes.push(
        <em key={`i-${match.index}`} className="text-gray-400 italic">
          {content}
        </em>
      );
    }

    lastIndex = match.index + full.length;
  }

  // Kalan metin
  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes.length > 0 ? nodes : [text];
}

/**
 * Markdown metni satir satir parse edip JSX'e donusturur.
 */
export function MarkdownRenderer({ text }: MarkdownRendererProps) {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let listBuffer: React.ReactNode[] = [];
  let listType: 'bullet' | 'number' | null = null;

  const flushList = () => {
    if (listBuffer.length > 0) {
      if (listType === 'number') {
        elements.push(
          <ol key={`ol-${elements.length}`} className="list-decimal list-inside space-y-0.5 my-1">
            {listBuffer}
          </ol>
        );
      } else {
        elements.push(
          <ul key={`ul-${elements.length}`} className="space-y-0.5 my-1">
            {listBuffer}
          </ul>
        );
      }
      listBuffer = [];
      listType = null;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Separator: ─── (3+ dash veya box drawing)
    if (/^[─━─]{3,}/.test(line.trim()) || /^[-]{3,}$/.test(line.trim())) {
      flushList();
      elements.push(
        <hr
          key={`hr-${i}`}
          className="border-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent my-2"
        />
      );
      continue;
    }

    // Bos satir
    if (line.trim() === '') {
      flushList();
      elements.push(<div key={`sp-${i}`} className="h-1.5" />);
      continue;
    }

    // Bullet list: - item veya · item
    const bulletMatch = line.match(/^\s*[-·•]\s+(.+)/);
    if (bulletMatch) {
      if (listType !== 'bullet') {
        flushList();
        listType = 'bullet';
      }
      listBuffer.push(
        <li key={`li-${i}`} className="flex items-start gap-1.5 text-gray-300">
          <span className="text-neon-cyan mt-1 text-[8px]">●</span>
          <span>{parseInline(bulletMatch[1])}</span>
        </li>
      );
      continue;
    }

    // Numbered list: 1. item
    const numMatch = line.match(/^\s*(\d+)\.\s+(.+)/);
    if (numMatch) {
      if (listType !== 'number') {
        flushList();
        listType = 'number';
      }
      listBuffer.push(
        <li key={`li-${i}`} className="flex items-start gap-1.5 text-gray-300">
          <span className="text-neon-cyan font-mono text-xs min-w-[1.2rem] text-right">{numMatch[1]}.</span>
          <span>{parseInline(numMatch[2])}</span>
        </li>
      );
      continue;
    }

    // Indent satiri (2+ bosluk ile baslar, bullet degil)
    if (line.match(/^\s{2,}/) && !bulletMatch) {
      flushList();
      elements.push(
        <div key={`ind-${i}`} className="pl-4 text-gray-300">
          {parseInline(line.trimStart())}
        </div>
      );
      continue;
    }

    // Normal satir
    flushList();
    elements.push(
      <div key={`p-${i}`} className="text-gray-200">
        {parseInline(line)}
      </div>
    );
  }

  flushList();

  return <div className="space-y-0.5">{elements}</div>;
}

export default MarkdownRenderer;
