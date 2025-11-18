import { ChevronDownIcon, ChevronRightIcon, WrenchIcon } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import type { ToolCall } from '@/stores/chatStore';

interface ToolCallCardProps {
  toolCall: ToolCall;
}

export const ToolCallCard = ({ toolCall }: ToolCallCardProps) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // 解析参数（可能是字符串或对象）
  const parseArguments = () => {
    try {
      if (typeof toolCall.arguments === 'string') {
        return JSON.parse(toolCall.arguments);
      }
      return toolCall.input || toolCall.arguments || {};
    } catch {
      return toolCall.arguments || toolCall.input || {};
    }
  };

  const args = parseArguments();

  return (
    <Card className="my-2 border-l-4 border-l-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/20">
      <CardHeader className="p-3 pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <WrenchIcon size={16} className="text-emerald-600 dark:text-emerald-400" />
            <span className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">
              工具调用: {toolCall.name}
            </span>
          </div>
          <Button variant="ghost" size="sm" onClick={() => setIsExpanded(!isExpanded)} className="h-6 w-6 p-0">
            {isExpanded ? <ChevronDownIcon size={16} /> : <ChevronRightIcon size={16} />}
          </Button>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="p-3 pt-0 space-y-2">
          {/* 输入参数 */}
          {args && Object.keys(args).length > 0 && (
            <div>
              <div className="text-xs font-semibold text-muted-foreground mb-1">Parameters:</div>
              <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">{JSON.stringify(args, null, 2)}</pre>
            </div>
          )}

          {/* 输出结果 */}
          {toolCall.output && (
            <div>
              <div className="text-xs font-semibold text-muted-foreground mb-1">Tool Output:</div>
              <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                {typeof toolCall.output === 'string' ? toolCall.output : JSON.stringify(toolCall.output, null, 2)}
              </pre>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
};
