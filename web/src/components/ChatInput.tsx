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
    <div className="border-t bg-card p-3 sm:p-4 shadow-lg">
      <div className="max-w-full sm:max-w-3xl md:max-w-4xl lg:max-w-5xl xl:max-w-6xl 2xl:max-w-7xl mx-auto px-2 sm:px-0">
        <div className="flex items-end gap-2">
          {/* 工具调用显示开关 */}
          <div className="flex flex-col items-center gap-1 pb-2">
            <Switch
              id="show-tool-calls"
              checked={settings.show_tool_calls}
              onCheckedChange={handleToggleToolCalls}
              title="显示工具调用信息"
            />
            <Label htmlFor="show-tool-calls" className="text-xs text-muted-foreground cursor-pointer">
              工具
            </Label>
          </div>

          <Textarea
            ref={textareaRef}
            value={message}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="输入消息... (Shift + Enter 换行)"
            disabled={disabled}
            maxLength={maxLength}
            className="flex-1 resize-none max-h-32 sm:max-h-40 min-h-[50px] sm:min-h-[60px] border-2 focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all duration-200 rounded-xl text-sm sm:text-base"
            rows={1}
          />
          {isSending ? (
            <Button
              onClick={onStop}
              variant="destructive"
              size="icon"
              className="h-[50px] w-[50px] sm:h-[60px] sm:w-[60px] shadow-lg hover:shadow-xl transform hover:scale-105 active:scale-95 transition-all duration-200"
              title="停止生成"
            >
              <StopCircleIcon className="w-5 h-5 sm:w-6 sm:h-6" />
            </Button>
          ) : (
            <Button
              onClick={handleSend}
              disabled={disabled || !message.trim()}
              size="icon"
              className="h-[50px] w-[50px] sm:h-[60px] sm:w-[60px] bg-gradient-to-r from-emerald-400 to-slate-500 hover:from-emerald-500 hover:to-slate-600 shadow-lg hover:shadow-xl transform hover:scale-105 active:scale-95 transition-all duration-200"
              title="发送消息"
            >
              <SendIcon className="w-5 h-5 sm:w-6 sm:h-6" />
            </Button>
          )}
          {showReset && onReset && (
            <Button
              onClick={onReset}
              variant="outline"
              size="icon"
              className="h-[50px] w-[50px] sm:h-[60px] sm:w-[60px] hover:border-primary hover:bg-accent transform hover:scale-105 active:scale-95 transition-all duration-200"
              title="重置对话"
            >
              <RotateCcwIcon className="w-5 h-5 sm:w-6 sm:h-6" />
            </Button>
          )}
        </div>
        <div className="mt-2 flex justify-between items-center px-1">
          <p className="text-xs text-muted-foreground hidden sm:block">按 Enter 发送，Shift + Enter 换行</p>
          <p className="text-xs text-muted-foreground sm:hidden">Enter 发送</p>
          <span
            className={`text-xs transition-colors ${
              message.length > maxLength * 0.9 ? 'text-destructive font-medium' : 'text-muted-foreground'
            }`}
          >
            {message.length}/{maxLength}
          </span>
        </div>
      </div>
    </div>
  );
};
