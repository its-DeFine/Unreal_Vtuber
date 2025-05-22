import { describe, expect, it } from 'vitest';
import { convertMarkdownToTelegram, splitMessage } from '../src/utils';

describe('Telegram Utils', () => {
  describe('splitMessage', () => {
    it('should not split message within limit', () => {
      const message = 'Hello World';
      const chunks = splitMessage(message, 4096);
      expect(chunks).toEqual(['Hello World']);
    });

    it('should handle empty string', () => {
      const chunks = splitMessage('');
      expect(chunks).toEqual([]);
    });

    it('should keep message intact if shorter than maxLength', () => {
      const message = 'Hello World';
      const chunks = splitMessage(message, 6);
      expect(chunks).toEqual(['Hello World']);
    });
  });

  describe('convertMarkdownToTelegram', () => {
    it('should handle text without special characters', () => {
      const input = 'Hello World 123';
      expect(convertMarkdownToTelegram(input)).toBe(input);
    });

    it('should handle empty string', () => {
      expect(convertMarkdownToTelegram('')).toBe('');
    });

    it('should convert headers to bold text', () => {
      const result = convertMarkdownToTelegram('# Header 1\n## Header 2');
      expect(result).toContain('*Header 1*');
      expect(result).toContain('*Header 2*');
    });

    it('should convert bold text correctly', () => {
      const result = convertMarkdownToTelegram('This is **bold text**');
      expect(result).toBe('This is *bold text*');
    });

    it('should convert italic text correctly', () => {
      const result = convertMarkdownToTelegram('This is *italic text*');
      expect(result).toBe('This is _italic text_');
    });

    it('should convert strikethrough text correctly', () => {
      const result = convertMarkdownToTelegram('This is ~~strikethrough text~~');
      expect(result).toBe('This is ~strikethrough text~');
    });

    it('should convert inline code correctly', () => {
      const result = convertMarkdownToTelegram('This is `inline code`');
      expect(result).toBe('This is `inline code`');
    });

    it('should convert links correctly', () => {
      const result = convertMarkdownToTelegram('[Google](https://www.google.com)');
      expect(result).toBe('\\[Google\\]\\(https://www\\.google\\.com\\)');
    });

    it('should convert code blocks correctly', () => {
      const result = convertMarkdownToTelegram('```javascript\nconsole.log("test");\n```');
      expect(result).toContain('```javascript');
      expect(result).toContain('```javascript\nconsole.log(\"test\");\n```');
    });

    it('should convert blockquotes correctly', () => {
      const result = convertMarkdownToTelegram('> This is a blockquote');
      expect(result).toBe('> This is a blockquote');
    });

    it('should escape special characters correctly', () => {
      const result = convertMarkdownToTelegram(
        'These chars: _ * [ ] ( ) ~ ` > # + - = | { } . ! \\'
      );
      expect(result).toBe(
        'These chars: \\_ \\* \\[ \\] \\( \\) \\~ \\` \\> \\# \\+ \\- \\= \\| \\{ \\} \\. \\! \\\\'
      );
    });

    it('should handle mixed formatting correctly', () => {
      const result = convertMarkdownToTelegram(
        '**Bold** and *italic* and `code` and ~~strikethrough~~'
      );
      expect(result).toBe('*Bold* and _italic_ and `code` and ~strikethrough~');
    });

    it('should handle nested formatting correctly', () => {
      const result = convertMarkdownToTelegram('**Bold and *italic***');
      expect(result).toBe('\\*\\*Bold and \\*italic\\*\\*\\*');
    });

    it('should handle URLs with special characters correctly', () => {
      const result = convertMarkdownToTelegram('[Link](https://example.com/path(with)parentheses)');
      expect(result).toBe('\\[Link\\]\\(https://example\\.com/path\\(with\\)parentheses\\)');
    });
  });
});
