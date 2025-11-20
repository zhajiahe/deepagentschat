import { RotateCcwIcon, SendIcon, StopCircleIcon } from 'lucide-react';
import { type KeyboardEvent, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { useUserSettingsStore } from '@/stores/userSettingsStore';

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  onReset?: () => void;
  disabled?: boolean;
  isSending?: boolean;
  showReset?: boolean;
}

export const ChatInput = ({ onSend, onStop, onReset, disabled, isSending, showReset }: ChatInputProps) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { settings, updateShowToolCalls } = useUserSettingsStore();
  const { toast } = useToast();
  const maxLength = 2000;

  const handleToggleToolCalls = async (checked: boolean) => {
    try {
      await updateShowToolCalls(checked);
      toast({
        title: '设置已更新',
        description: `工具调用显示已${checked ? '开启' : '关闭'}`,
      });
    } catch (error) {
      console.error('Failed to update tool calls setting:', error);
      toast({
        title: '更新失败',
        description: '无法更新工具调用显示设置',
        variant: 'destructive',
      });
    }
  };

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    // 自动调整高度
    e.target.style.height = 'auto';
    e.target.style.height = `${e.target.scrollHeight}px`;
  };

  return (
    <div className="bg-card dark:bg-grokbg p-4">
      <div className="max-w-4xl mx-auto">
        <div className="relative">
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything..."
            disabled={disabled}
            maxLength={maxLength}
            className="w-full bg-muted dark:bg-grokgray text-foreground dark:text-groktext placeholder-muted-foreground dark:placeholder-groksub rounded-grok px-6 py-5 pr-32 text-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all max-h-[200px] min-h-[60px]"
            rows={1}
          />
          <div className="absolute right-4 bottom-4 flex items-center gap-2">
            {/* 工具调用显示开关 */}
            <div className="flex items-center gap-1">
              <Switch
                id="show-tool-calls"
                checked={settings.show_tool_calls}
                onCheckedChange={handleToggleToolCalls}
                title="显示工具调用信息"
              />
              <Label
                htmlFor="show-tool-calls"
                className="text-xs text-muted-foreground dark:text-groksub cursor-pointer"
              >
                工具
              </Label>
            </div>

            {showReset && onReset && (
              <Button
                onClick={onReset}
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-muted-foreground dark:text-groksub hover:text-foreground dark:hover:text-white transition"
                title="重置对话"
              >
                <RotateCcwIcon size={18} />
              </Button>
            )}

            {isSending ? (
              <Button
                onClick={onStop}
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-muted-foreground dark:text-groksub hover:text-foreground dark:hover:text-white transition"
                title="停止生成"
              >
                <StopCircleIcon size={24} />
              </Button>
            ) : (
              <Button
                onClick={handleSend}
                disabled={disabled || !message.trim()}
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-muted-foreground dark:text-groksub hover:text-foreground dark:hover:text-white transition disabled:opacity-50"
                title="发送消息"
              >
                <SendIcon size={24} />
              </Button>
            )}
          </div>
        </div>
        <p className="text-xs text-muted-foreground dark:text-groksub text-center mt-3">
          Grok can make mistakes. Consider checking important information.
        </p>
      </div>
    </div>
  );
};
