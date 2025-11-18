import { useState } from 'react';

interface ToolCall {
  name: string;
  arguments?: any;
  input?: any;
  output?: any;
}

interface ToolCallMessageProps {
  toolCall: ToolCall;
  messageId: number;
}

export const ToolCallMessage = ({ toolCall, messageId }: ToolCallMessageProps) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="space-y-2">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between text-orange-700 dark:text-orange-400 font-semibold hover:opacity-80 transition-opacity"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">🔧</span>
          <span>调用工具: {toolCall.name}</span>
        </div>
        <span className="text-sm">{isExpanded ? '▼' : '▶'}</span>
      </button>

      {/* 简洁显示输入参数 */}
      {!isExpanded && (toolCall.arguments || toolCall.input) && (
        <div className="text-xs text-muted-foreground truncate">
          参数: {JSON.stringify(toolCall.arguments || toolCall.input)}
        </div>
      )}

      {isExpanded && (
        <div className="space-y-2 animate-slide-up">
          {(toolCall.arguments || toolCall.input) && (
            <div>
              <div className="text-sm text-muted-foreground mb-1">输入参数：</div>
              <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                {JSON.stringify(toolCall.arguments || toolCall.input, null, 2)}
              </pre>
            </div>
          )}
          {toolCall.output && (
            <div>
              <div className="text-sm text-muted-foreground mb-1">输出结果：</div>
              <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-40">
                {typeof toolCall.output === 'string' ? toolCall.output : JSON.stringify(toolCall.output, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
